# src/auth_routes.py - CORRECTED VERSION for Azure production
import os
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import traceback
import json

# CRITICAL FIX: Allow insecure transport for development only
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
        
        # Check if we have user info in session
        user_info = session.get('user_info')
        if not user_info:
            logger.info("🔍 DEBUG: No user_info in session")
            return jsonify({
                "authenticated": False,
                "needsAuth": True
            }), 401

        logger.info(f"🔍 DEBUG: User info found: {user_info.get('email', 'No email')}")
        
        # Get user from database to check limits
        try:
            user = get_user_by_email(user_info.get('email'))
            if user:
                # Add usage limits to response
                from src.db.usage import check_user_limits
                usage = check_user_limits(user['id'], request.remote_addr)
                
                return jsonify({
                    "authenticated": True,
                    "user": {
                        "id": user['id'],
                        "email": user_info.get('email'),
                        "name": user_info.get('name'),
                        "picture": user_info.get('picture'),
                        "is_premium": False
                    },
                    "usage_limits": {
                        "generations_left": usage['generations_left'],
                        "downloads_left": usage['downloads_left'],
                        "reset_time": usage['reset_time'],
                        "is_premium": False,
                        "current_usage": usage['current_usage']
                    }
                })
        except Exception as db_error:
            logger.error(f"❌ Database error in auth check: {db_error}")
            # Return basic auth info even if DB fails
            return jsonify({
                "authenticated": True,
                "user": {
                    "email": user_info.get('email'),
                    "name": user_info.get('name'),
                    "picture": user_info.get('picture')
                }
            })
        
        return jsonify({
            "authenticated": True,
            "user": {
                "email": user_info.get('email'),
                "name": user_info.get('name'),
                "picture": user_info.get('picture')
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
        logger.info(f"🔍 Environment: {os.environ.get('FLASK_ENV', 'unknown')}")
        logger.info(f"🔍 Development Mode: {config.DEVELOPMENT_MODE}")
        
        if not flow:
            logger.error("❌ OAuth flow not initialized")
            return jsonify({"error": "OAuth not configured"}), 500
            
        logger.info(f"🔍 Flow redirect URI: {flow.redirect_uri}")
        
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
    """Handle Google OAuth callback with Azure-compatible URL handling."""
    try:
        logger.info("🔐 OAuth callback received")
        logger.info(f"🔍 Request URL: {request.url}")
        logger.info(f"🔍 Request args: {dict(request.args)}")
        logger.info(f"🔍 Environment: {os.environ.get('FLASK_ENV', 'unknown')}")
        logger.info(f"🔍 Development Mode: {config.DEVELOPMENT_MODE}")
        logger.info(f"🔍 Request headers - X-Forwarded-Proto: {request.headers.get('X-Forwarded-Proto', 'Not set')}")
        logger.info(f"🔍 Request is_secure: {request.is_secure}")
        
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
                    <p>Description: {error_description}</p>
                    <script>
                        console.error('OAuth error:', '{error}');
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Authentication failed: {error} - {error_description}'
                            }}, '*');
                            window.close();
                        }} else {{
                            setTimeout(() => {{
                                window.location.href = '/';
                            }}, 3000);
                        }}
                    </script>
                </body>
                </html>
            """
        
        # Check if we have an authorization code
        if 'code' not in request.args:
            logger.error("❌ No authorization code in callback")
            return """
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>No authorization code received</p>
                    <script>
                        console.error('No authorization code received');
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
        
        # CORRECTED: Handle Azure App Service URL correctly
        try:
            logger.info("🔍 Attempting to fetch token...")
            logger.info(f"🔍 Flow redirect_uri: {flow.redirect_uri}")
            
            # AZURE FIX: Construct the correct authorization response URL
            auth_response = request.url
            
            # For Azure App Service, check if we need to fix the scheme
            if not config.DEVELOPMENT_MODE:
                # Azure App Service uses X-Forwarded-Proto header
                forwarded_proto = request.headers.get('X-Forwarded-Proto', 'https')
                
                # If the request URL is HTTP but should be HTTPS (Azure internal routing)
                if auth_response.startswith('http://') and forwarded_proto == 'https':
                    auth_response = auth_response.replace('http://', 'https://', 1)
                    logger.info(f"🔒 Fixed Azure URL scheme: {auth_response}")
                
                # Ensure the host matches the configured redirect URI
                from urllib.parse import urlparse, urlunparse
                parsed_auth = urlparse(auth_response)
                parsed_redirect = urlparse(flow.redirect_uri)
                
                # Replace host/scheme if they don't match
                if parsed_auth.netloc != parsed_redirect.netloc or parsed_auth.scheme != parsed_redirect.scheme:
                    fixed_auth = parsed_auth._replace(
                        scheme=parsed_redirect.scheme,
                        netloc=parsed_redirect.netloc
                    )
                    auth_response = urlunparse(fixed_auth)
                    logger.info(f"🔧 Fixed Azure host/scheme: {auth_response}")
            
            logger.info(f"🔍 Final auth_response URL: {auth_response}")
            
            # CRITICAL: Clear any existing OAUTHLIB_INSECURE_TRANSPORT in production
            if not config.DEVELOPMENT_MODE and 'OAUTHLIB_INSECURE_TRANSPORT' in os.environ:
                del os.environ['OAUTHLIB_INSECURE_TRANSPORT']
                logger.info("🔒 Removed OAUTHLIB_INSECURE_TRANSPORT for production")
            
            flow.fetch_token(authorization_response=auth_response)
            credentials = flow.credentials
            logger.info("✅ Token fetched successfully")
            
        except Exception as token_error:
            logger.error(f"❌ Token fetch error: {token_error}")
            logger.error(f"❌ Token error type: {type(token_error).__name__}")
            logger.error(traceback.format_exc())
            
            # Provide more specific error information
            error_details = str(token_error)
            if "invalid_grant" in error_details.lower():
                error_msg = "Authentication session expired. Please try signing in again."
            elif "redirect_uri_mismatch" in error_details.lower():
                error_msg = "OAuth configuration error. Please contact support."
                logger.error(f"❌ REDIRECT URI MISMATCH - Flow URI: {flow.redirect_uri}, Request URL: {request.url}")
            elif "invalid_client" in error_details.lower():
                error_msg = "Client authentication failed. Please contact support."
            else:
                error_msg = f"Authentication failed: {error_details}"
            
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>{error_msg}</p>
                    <p><small>Technical details: {error_details}</small></p>
                    <script>
                        console.error('Token fetch error:', '{error_details}');
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: '{error_msg}'
                            }}, '*');
                            window.close();
                        }}
                    </script>
                </body>
                </html>
            """
        
        # Store credentials in session
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        logger.info("💾 Credentials stored in session")

        # Verify token and get user info
        try:
            logger.info("🔍 Verifying ID token...")
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                CLIENT_ID,
                clock_skew_in_seconds=300
            )
            logger.info(f"✅ Token verified for user: {id_info.get('email')}")
        except Exception as verify_error:
            logger.error(f"❌ Token verification error: {verify_error}")
            logger.error(traceback.format_exc())
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>Failed to verify authentication token</p>
                    <script>
                        console.error('Token verification error:', '{str(verify_error)}');
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Failed to verify authentication token'
                            }}, '*');
                            window.close();
                        }}
                    </script>
                </body>
                </html>
            """

        # Store user info in session
        user_info = {
            'email': id_info['email'],
            'name': id_info.get('name', ''),
            'picture': id_info.get('picture', '')
        }
        session['user_info'] = user_info
        session.permanent = True
        logger.info("💾 User info stored in session")

        # Create/update user in database and log login
        user_id = None
        try:
            logger.info(f"🔍 Creating/updating user in database: {user_info['email']}")
            user_id = create_user(user_info['email'], user_info['name'], user_info['picture'])
            
            if user_id:
                log_user_login(user_id)
                logger.info(f"✅ User login logged for ID: {user_id}")
                session['user_id'] = user_id
            else:
                logger.warning("⚠️ Could not get user ID for login logging")
                
        except Exception as db_error:
            logger.error(f"❌ Database error during OAuth: {db_error}")
            logger.error(traceback.format_exc())
        
        logger.info(f"✅ Successfully authenticated user: {user_info['email']}")
        
        # Return success page that communicates with parent window
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
                    .checkmark {{
                        font-size: 3rem;
                        margin-bottom: 20px;
                    }}
                    .loading {{
                        display: inline-block;
                        width: 20px;
                        height: 20px;
                        border: 3px solid #f3f3f3;
                        border-top: 3px solid #2d5fcf;
                        border-radius: 50%;
                        animation: spin 1s linear infinite;
                        margin-left: 10px;
                    }}
                    @keyframes spin {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                </style>
            </head>
            <body>
                <div class="success">
                    <div class="checkmark">✅</div>
                    <h2>Authentication Successful!</h2>
                    <p>Welcome, {user_info.get('name', user_info['email'])}!</p>
                    <p>Redirecting back to the app<span class="loading"></span></p>
                </div>
                
                <script>
                    console.log('🎉 OAuth success! User authenticated:', {{
                        email: '{user_info['email']}',
                        name: '{user_info.get('name', '')}',
                        user_id: {user_id or 'null'}
                    }});
                    
                    // Send success message to parent window
                    try {{
                        if (window.opener) {{
                            console.log('📨 Sending success message to parent window...');
                            
                            window.opener.postMessage({{
                                type: 'AUTH_SUCCESS',
                                user: {{
                                    email: '{user_info['email']}',
                                    name: '{user_info.get('name', '')}',
                                    picture: '{user_info.get('picture', '')}',
                                    id: {user_id or 'null'}
                                }}
                            }}, '*');
                            
                            console.log('✅ Success message sent, closing popup...');
                            setTimeout(() => {{
                                window.close();
                            }}, 2000);
                        }} else {{
                            console.log('ℹ️ No opener window, redirecting to home...');
                            setTimeout(() => {{
                                window.location.href = '/';
                            }}, 2000);
                        }}
                    }} catch (error) {{
                        console.error('❌ Error in OAuth callback script:', error);
                        setTimeout(() => {{
                            window.close();
                        }}, 3000);
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
                    console.error('OAuth callback error:', '{str(e)}');
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'AUTH_ERROR',
                            error: 'Authentication failed: {str(e)}'
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