# src/auth_routes.py - FIXED session management
import os
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import traceback
import json

if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from src.config import logger, flow, CLIENT_ID, config
from src.db import get_user_by_email, create_user, log_user_login, log_user_activity

auth_blueprint = Blueprint("auth_blueprint", __name__)

@auth_blueprint.route('/auth/check', methods=['GET'])
def check_auth():
    """Check if the user is authenticated and session is valid."""
    try:
        logger.info("🔍 DEBUG: /auth/check route called")
        logger.info(f"🔍 DEBUG: Session keys: {list(session.keys())}")
        
        user_info = session.get('user_info')
        if not user_info:
            logger.info("🔍 DEBUG: No user_info in session")
            return jsonify({
                "authenticated": False,
                "needsAuth": True
            }), 401

        logger.info(f"🔍 DEBUG: User info found: {user_info.get('email', 'No email')}")
        
        try:
            user = get_user_by_email(user_info.get('email'))
            if user:
                from src.db.usage import check_user_limits, get_user_subscription_tier
                
                user_tier = get_user_subscription_tier(user['id'], user_info.get('email'))
                usage = check_user_limits(user['id'], request.remote_addr)
                
                return jsonify({
                    "authenticated": True,
                    "user": {
                        "id": user['id'],
                        "email": user_info.get('email'),
                        "name": user_info.get('name'),
                        "picture": user_info.get('picture'),
                        "is_premium": user_tier == 'premium',
                        "subscription_tier": user_tier,
                        "subscription_status": user.get('subscription_status', 'active')
                    },
                    "usage_limits": {
                        "generations_left": usage['generations_left'],
                        "downloads_left": usage['downloads_left'],
                        "reset_time": usage['reset_time'],
                        "is_premium": user_tier == 'premium',
                        "user_tier": user_tier,
                        "current_usage": usage['current_usage']
                    }
                })
        except Exception as db_error:
            logger.error(f"❌ Database error in auth check: {db_error}")
            return jsonify({
                "authenticated": True,
                "user": {
                    "email": user_info.get('email'),
                    "name": user_info.get('name'),
                    "picture": user_info.get('picture'),
                    "is_premium": False,
                    "subscription_tier": "free"
                }
            })
        
        return jsonify({
            "authenticated": True,
            "user": {
                "email": user_info.get('email'),
                "name": user_info.get('name'),
                "picture": user_info.get('picture'),
                "is_premium": False,
                "subscription_tier": "free"
            }
        })
    except Exception as e:
        logger.error(f"❌ Error checking auth status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "authenticated": False,
            "error": str(e)
        }), 500

@auth_blueprint.route('/authorize')
def authorize():
    """Initiate Google OAuth with the proper redirect URI."""
    try:
        logger.info("🔐 Starting OAuth authorization")
        
        if not flow:
            logger.error("❌ OAuth flow not initialized")
            return jsonify({"error": "OAuth not configured"}), 500
            
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        session['state'] = state
        logger.info(f"🔗 Redirecting to: {authorization_url}")
        
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"❌ Error during OAuth authorization: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/oauth2callback')
def oauth2callback():
    """Handle Google OAuth callback with proper session management."""
    try:
        logger.info("🔐 OAuth callback received")
        
        # Check for error in callback
        if 'error' in request.args:
            error = request.args.get('error')
            error_description = request.args.get('error_description', '')
            logger.error(f"❌ OAuth error in callback: {error} - {error_description}")
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>Error: {error}</p>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Authentication failed: {error}'
                            }}, '*');
                            window.close();
                        }}
                    </script>
                </body>
                </html>
            """
        
        if 'code' not in request.args:
            logger.error("❌ No authorization code in callback")
            return """
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>No authorization code received</p>
                    <script>
                        if (window.opener) {
                            window.opener.postMessage({
                                type: 'AUTH_ERROR',
                                error: 'No authorization code received'
                            }, '*');
                            window.close();
                        }
                    </script>
                </body>
                </html>
            """
        
        # Handle token exchange
        try:
            auth_response = request.url
            
            if not config.DEVELOPMENT_MODE:
                forwarded_proto = request.headers.get('X-Forwarded-Proto', 'https')
                
                if auth_response.startswith('http://') and forwarded_proto == 'https':
                    auth_response = auth_response.replace('http://', 'https://', 1)
                
                from urllib.parse import urlparse, urlunparse
                parsed_auth = urlparse(auth_response)
                parsed_redirect = urlparse(flow.redirect_uri)
                
                if parsed_auth.netloc != parsed_redirect.netloc or parsed_auth.scheme != parsed_redirect.scheme:
                    fixed_auth = parsed_auth._replace(
                        scheme=parsed_redirect.scheme,
                        netloc=parsed_redirect.netloc
                    )
                    auth_response = urlunparse(fixed_auth)
            
            flow.fetch_token(authorization_response=auth_response)
            credentials = flow.credentials
            logger.info("✅ Token fetched successfully")
            
        except Exception as token_error:
            logger.error(f"❌ Token fetch error: {token_error}")
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>Failed to exchange authorization code</p>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Token exchange failed'
                            }}, '*');
                            window.close();
                        }}
                    </script>
                </body>
                </html>
            """
        
        # FIXED: Store only essential credentials to reduce session size
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret
            # Removed 'scopes' to reduce session size
        }
        logger.info("💾 Credentials stored in session")

        # Verify token and get user info
        try:
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                CLIENT_ID,
                clock_skew_in_seconds=300
            )
            logger.info(f"✅ Token verified for user: {id_info.get('email')}")
        except Exception as verify_error:
            logger.error(f"❌ Token verification error: {verify_error}")
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>Failed to verify authentication token</p>
                    <script>
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Token verification failed'
                            }}, '*');
                            window.close();
                        }}
                    </script>
                </body>
                </html>
            """

        # FIXED: Store minimal user info to reduce session size
        user_info = {
            'email': id_info['email'],
            'name': id_info.get('name', ''),
            'picture': id_info.get('picture', '')
        }
        session['user_info'] = user_info
        session.permanent = True
        logger.info("💾 User info stored in session")

        # Create/update user in database
        user_id = None
        try:
            user_id = create_user(user_info['email'], user_info['name'], user_info['picture'])
            
            if user_id:
                # FIXED: Only try to update subscription fields if they exist
                try:
                    from src.db.database import get_db_cursor
                    with get_db_cursor(commit=True) as cursor:
                        # Check if subscription columns exist first
                        cursor.execute("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = 'users' 
                            AND column_name IN ('subscription_tier', 'subscription_status')
                        """)
                        existing_columns = [row['column_name'] for row in cursor.fetchall()]
                        
                        if 'subscription_tier' in existing_columns and 'subscription_status' in existing_columns:
                            cursor.execute("""
                                UPDATE users 
                                SET subscription_tier = COALESCE(subscription_tier, 'free'),
                                    subscription_status = COALESCE(subscription_status, 'active')
                                WHERE id = %s
                            """, (user_id,))
                            logger.info("✅ Subscription fields updated")
                        else:
                            logger.warning("⚠️ Subscription columns don't exist yet - skipping update")
                except Exception as subscription_error:
                    logger.warning(f"⚠️ Could not update subscription fields: {subscription_error}")
                    # Continue anyway - this is not critical for login
                
                log_user_login(user_id)
                session['user_id'] = user_id
                logger.info(f"✅ User login logged for ID: {user_id}")
                
        except Exception as db_error:
            logger.error(f"❌ Database error during OAuth: {db_error}")
            # Continue with OAuth even if DB update fails
        
        logger.info(f"✅ Successfully authenticated user: {user_info['email']}")
        
        # Return success page
        return f"""
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {{ 
                        font-family: Arial, sans-serif; 
                        padding: 20px; 
                        text-align: center;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        min-height: 100vh;
                        display: flex;
                        flex-direction: column;
                        justify-content: center;
                        align-items: center;
                    }}
                    .success {{ 
                        background: white;
                        color: #2d5fcf;
                        padding: 30px;
                        border-radius: 15px;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
                        max-width: 400px;
                    }}
                </style>
            </head>
            <body>
                <div class="success">
                    <div style="font-size: 3rem; margin-bottom: 20px;">✅</div>
                    <h2>Authentication Successful!</h2>
                    <p>Welcome, {user_info.get('name', user_info['email'])}!</p>
                    <p>Redirecting back to the app...</p>
                </div>
                
                <script>
                    console.log('🎉 OAuth success! User authenticated');
                    
                    try {{
                        if (window.opener && !window.opener.closed) {{
                            console.log('📨 Sending success message to parent window...');
                            
                            window.opener.postMessage({{
                                type: 'AUTH_SUCCESS',
                                user: {{
                                    email: '{user_info['email']}',
                                    name: '{user_info.get('name', '')}',
                                    picture: '{user_info.get('picture', '')}',
                                    id: {user_id or 'null'},
                                    is_premium: false,
                                    subscription_tier: 'free'
                                }}
                            }}, window.location.origin);
                            
                            console.log('✅ Success message sent, closing popup...');
                            setTimeout(() => {{
                                window.close();
                            }}, 1000);
                        }} else {{
                            console.log('ℹ️ No opener window, redirecting to home...');
                            setTimeout(() => {{
                                window.location.href = '/';
                            }}, 2000);
                        }}
                    }} catch (error) {{
                        console.error('❌ Error in OAuth callback script:', error);
                        setTimeout(() => {{
                            try {{
                                window.close();
                            }} catch (e) {{
                                window.location.href = '/';
                            }}
                        }}, 2000);
                    }}
                </script>
            </body>
            </html>
        """
    except Exception as e:
        logger.error(f"❌ OAuth callback error: {e}")
        logger.error(traceback.format_exc())
        return f"""
            <html>
            <head><title>Authentication Error</title></head>
            <body>
                <h2>Authentication Error</h2>
                <p>An unexpected error occurred during authentication</p>
                <script>
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'AUTH_ERROR',
                            error: 'Authentication failed'
                        }}, '*');
                        window.close();
                    }}
                </script>
            </body>
            </html>
        """

@auth_blueprint.route('/logout')
def logout():
    """Clear session and log out user."""
    try:
        user_email = session.get('user_info', {}).get('email', 'Unknown')
        logger.info(f"🚪 Logging out user: {user_email}")
        
        session.clear()
        logger.info("✅ Session cleared")
        
        return jsonify({"message": "Logged out successfully"})
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        return jsonify({"error": str(e)}), 500