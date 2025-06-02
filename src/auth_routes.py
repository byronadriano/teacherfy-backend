# src/auth_routes.py - FIXED OAuth callback to prevent main site loading in popup
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
    """Handle Google OAuth callback - FIXED to stay in popup and communicate properly."""
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
                        console.log('OAuth error occurred:', '{error}');
                        if (window.opener && !window.opener.closed) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Authentication failed: {error}'
                            }}, '*');
                        }}
                        setTimeout(() => window.close(), 2000);
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
                        console.log('No authorization code received');
                        if (window.opener && !window.opener.closed) {
                            window.opener.postMessage({
                                type: 'AUTH_ERROR',
                                error: 'No authorization code received'
                            }, '*');
                        }
                        setTimeout(() => window.close(), 2000);
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
                        console.log('Token exchange failed:', '{str(token_error)}');
                        if (window.opener && !window.opener.closed) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Token exchange failed'
                            }}, '*');
                        }}
                        setTimeout(() => window.close(), 2000);
                    </script>
                </body>
                </html>
            """
        
        # Store only essential credentials to reduce session size
        session['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret
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
                        console.log('Token verification failed:', '{str(verify_error)}');
                        if (window.opener && !window.opener.closed) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Token verification failed'
                            }}, '*');
                        }}
                        setTimeout(() => window.close(), 2000);
                    </script>
                </body>
                </html>
            """

        # Store minimal user info to reduce session size
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
                try:
                    from src.db.database import get_db_cursor
                    with get_db_cursor(commit=True) as cursor:
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
                
                log_user_login(user_id)
                session['user_id'] = user_id
                logger.info(f"✅ User login logged for ID: {user_id}")
                
        except Exception as db_error:
            logger.error(f"❌ Database error during OAuth: {db_error}")
        
        logger.info(f"✅ Successfully authenticated user: {user_info['email']}")
        
        # FIXED: Return popup-only success page that NEVER redirects to main site
        return f"""
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                    padding: 40px 20px;
                    text-align: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    min-height: 100vh;
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    margin: 0;
                }}
                .success {{ 
                    background: white;
                    color: #2d3748;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    max-width: 400px;
                    width: 100%;
                }}
                .status {{
                    margin-top: 20px;
                    padding: 12px;
                    border-radius: 8px;
                    background: #f7fafc;
                    border: 1px solid #e2e8f0;
                    font-size: 14px;
                    color: #4a5568;
                }}
                .success-icon {{
                    font-size: 4rem;
                    margin-bottom: 20px;
                    animation: bounce 2s infinite;
                }}
                @keyframes bounce {{
                    0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
                    40% {{ transform: translateY(-10px); }}
                    60% {{ transform: translateY(-5px); }}
                }}
            </style>
        </head>
        <body>
            <div class="success">
                <div class="success-icon">✅</div>
                <h2 style="margin: 0 0 10px 0; color: #2d3748;">Welcome to Teacherfy!</h2>
                <p style="margin: 0 0 20px 0; color: #718096;">
                    Hello, {user_info.get('name', user_info['email'])}!
                </p>
                <div class="status" id="status">
                    Completing sign-in...
                </div>
            </div>
            
            <script>
                console.log('🎉 OAuth success page loaded for popup');
                
                const status = document.getElementById('status');
                let messagesSent = 0;
                let maxAttempts = 10;
                let success = false;
                
                const userData = {{
                    email: '{user_info['email']}',
                    name: '{user_info.get('name', '')}',
                    picture: '{user_info.get('picture', '')}',
                    id: {user_id or 'null'},
                    is_premium: false,
                    subscription_tier: 'free'
                }};
                
                const message = {{
                    type: 'AUTH_SUCCESS',
                    user: userData
                }};
                
                function updateStatus(text) {{
                    status.textContent = text;
                    console.log('Status:', text);
                }}
                
                function sendMessage() {{
                    messagesSent++;
                    
                    console.log(`Attempt ${{messagesSent}}: Checking parent window...`);
                    
                    // CRITICAL: Prevent any redirects or navigation
                    if (messagesSent === 1) {{
                        updateStatus('Connecting to main window...');
                    }}
                    
                    try {{
                        // Check if opener exists and is not closed
                        if (!window.opener) {{
                            console.log('❌ No opener window found');
                            updateStatus('No parent window found');
                            
                            // CRITICAL: Don't redirect! Just show message
                            if (messagesSent > 5) {{
                                updateStatus('Please close this window manually');
                                return;
                            }}
                        }} else if (window.opener.closed) {{
                            console.log('❌ Opener window is closed');
                            updateStatus('Parent window was closed');
                            
                            // CRITICAL: Don't redirect! Just show message
                            if (messagesSent > 5) {{
                                updateStatus('Please close this window manually');
                                return;
                            }}
                        }} else {{
                            console.log('✅ Valid opener found, sending message...');
                            
                            try {{
                                // Send to specific origins
                                const origins = [
                                    'http://localhost:3000',
                                    'https://teacherfy.ai',
                                    window.location.origin
                                ];
                                
                                origins.forEach(origin => {{
                                    try {{
                                        window.opener.postMessage(message, origin);
                                        console.log(`📤 Message sent to ${{origin}}`);
                                    }} catch (e) {{
                                        console.log(`❌ Failed to send to ${{origin}}: ${{e.message}}`);
                                    }}
                                }});
                                
                                // Also send with wildcard
                                window.opener.postMessage(message, '*');
                                console.log('📤 Message sent with wildcard origin');
                                
                                success = true;
                                updateStatus('Success! You can close this window.');
                                
                                // Try to close after delay, but don't force redirect
                                setTimeout(() => {{
                                    try {{
                                        window.close();
                                        console.log('🔒 Window closed successfully');
                                    }} catch (e) {{
                                        console.log('ℹ️ Could not auto-close window:', e.message);
                                        updateStatus('Success! Please close this window.');
                                    }}
                                }}, 2000);
                                
                                return; // Success, stop trying
                                
                            }} catch (error) {{
                                console.log(`❌ Error sending message: ${{error.message}}`);
                                updateStatus('Communication error...');
                            }}
                        }}
                        
                        // If we get here, try again (but not forever)
                        if (messagesSent < maxAttempts) {{
                            updateStatus(`Retrying... (attempt ${{messagesSent}}/${{maxAttempts}})`);
                            setTimeout(sendMessage, 1000);
                        }} else {{
                            updateStatus('Unable to communicate with main window. Please close this window and refresh the main page.');
                            console.log('❌ Max attempts reached');
                        }}
                        
                    }} catch (error) {{
                        console.log(`❌ Unexpected error in sendMessage: ${{error.message}}`);
                        updateStatus('Unexpected error occurred');
                        
                        if (messagesSent < maxAttempts) {{
                            setTimeout(sendMessage, 1000);
                        }} else {{
                            updateStatus('Please close this window and refresh the main page.');
                        }}
                    }}
                }}
                
                // Start the process
                console.log('🚀 Starting message sending process...');
                sendMessage();
                
                // Also try at intervals
                setTimeout(sendMessage, 500);
                setTimeout(sendMessage, 1500);
                setTimeout(sendMessage, 3000);
                
                // Listen for messages from parent
                window.addEventListener('message', (event) => {{
                    console.log('📨 Received message from parent:', event.data);
                    if (event.data && event.data.type === 'POPUP_READY') {{
                        console.log('📡 Parent confirmed ready, sending auth data...');
                        sendMessage();
                    }}
                }});
                
                // CRITICAL: Prevent any navigation away from this page
                window.addEventListener('beforeunload', (event) => {{
                    console.log('⚠️ Popup is about to close/navigate');
                }});
                
                // CRITICAL: Override any location changes
                const originalReplace = window.location.replace;
                const originalAssign = window.location.assign;
                const originalHref = window.location.href;
                
                Object.defineProperty(window.location, 'href', {{
                    get: () => originalHref,
                    set: (value) => {{
                        console.log('🚫 Blocked attempt to navigate to:', value);
                        // Ignore navigation attempts
                    }}
                }});
                
                window.location.replace = (url) => {{
                    console.log('🚫 Blocked location.replace to:', url);
                    // Ignore replace attempts
                }};
                
                window.location.assign = (url) => {{
                    console.log('🚫 Blocked location.assign to:', url);
                    // Ignore assign attempts  
                }};
                
                console.log('🔒 Navigation blocking in place');
                
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
                    console.log('OAuth callback error:', '{str(e)}');
                    if (window.opener && !window.opener.closed) {{
                        window.opener.postMessage({{
                            type: 'AUTH_ERROR',
                            error: 'Authentication failed: {str(e)}'
                        }}, '*');
                    }}
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
            </html>
        """

# FIXED: Handle both GET and POST for logout
@auth_blueprint.route('/logout', methods=['GET', 'POST'])
def logout():
    """Clear session and log out user - handles both GET and POST."""
    try:
        user_email = session.get('user_info', {}).get('email', 'Unknown')
        logger.info(f"🚪 Logging out user: {user_email}")
        
        session.clear()
        logger.info("✅ Session cleared")
        
        # Handle different request methods
        if request.method == 'GET':
            # For GET requests, redirect to home page
            return redirect('/')
        else:
            # For POST requests, return JSON
            return jsonify({"message": "Logged out successfully"})
            
    except Exception as e:
        logger.error(f"❌ Logout error: {e}")
        if request.method == 'GET':
            return redirect('/?error=logout_failed')
        else:
            return jsonify({"error": str(e)}), 500