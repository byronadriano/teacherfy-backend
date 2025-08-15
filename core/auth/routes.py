# src/auth_routes.py - OAuth endpoints with new login initiation flow
import os
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import traceback
import json
import requests

if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from config.settings import logger, flow, CLIENT_ID, CLIENT_SECRET, config
from core.database import get_user_by_email, create_user, log_user_login, log_user_activity

auth_blueprint = Blueprint("auth_blueprint", __name__)

@auth_blueprint.route('/auth/check', methods=['GET'])
def check_auth():
    """Check if the user is authenticated and session is valid."""
    try:
        logger.info("🔍 Auth check called")
        
        # Check if user is in session (new session structure)
        if 'user_id' in session and 'user_email' in session:
            try:
                # Always verify current subscription status from database
                user = get_user_by_email(session['user_email'])
                if user:
                    from core.database.usage import check_user_limits, get_user_subscription_tier
                    
                    user_tier = get_user_subscription_tier(user['id'], session['user_email'])
                    usage = check_user_limits(user['id'], request.remote_addr)
                    
                    user_data = {
                        'id': session['user_id'],
                        'email': session['user_email'],
                        'name': session.get('user_name', ''),
                        'picture': session.get('user_picture', ''),
                        'is_premium': user_tier == 'premium',
                        'subscription_tier': user_tier,
                        'subscription_status': user.get('subscription_status', 'active')
                    }
                    
                    logger.info(f"✅ User {user_data['email']} verified as {user_tier}")
                    
                    return jsonify({
                        'authenticated': True,
                        'user': user_data,
                        "usage_limits": {
                            "generations_left": usage['generations_left'],
                            "downloads_left": usage['downloads_left'],
                            "reset_time": usage['reset_time'],
                            "is_premium": user_tier == 'premium',
                            "user_tier": user_tier,
                            "current_usage": usage['current_usage']
                        }
                    }), 200
                else:
                    logger.warning(f"User not found in database: {session['user_email']}")
            except Exception as db_error:
                logger.error(f"Database error checking user: {db_error}")
            
            # Fallback to session data if database check fails
            user_data = {
                'id': session['user_id'],
                'email': session['user_email'],
                'name': session.get('user_name', ''),
                'picture': session.get('user_picture', ''),
                'is_premium': session.get('is_premium', False),
                'subscription_tier': 'premium' if session.get('is_premium') else 'free'
            }
            
            logger.info(f"⚠️ Fallback to session data for user: {user_data['email']}")
            
            return jsonify({
                'authenticated': True,
                'user': user_data
            }), 200
        
        # Check legacy user_info structure
        user_info = session.get('user_info')
        if not user_info:
            logger.info("No authentication found in session")
            return jsonify({
                "authenticated": False,
                "user": None
            }), 401

        logger.info(f"Legacy session found for: {user_info.get('email', 'No email')}")
        
        try:
            user = get_user_by_email(user_info.get('email'))
            if user:
                from core.database.usage import check_user_limits, get_user_subscription_tier
                
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
            logger.error(f"Database error in legacy auth check: {db_error}")
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
        logger.error(f"Error checking auth status: {e}")
        return jsonify({
            "authenticated": False,
            "error": str(e)
        }), 401

# NEW OAUTH ENDPOINTS FOR FRONTEND-CONTROLLED FLOW

@auth_blueprint.route('/api/auth/login/<provider>', methods=['GET'])
def initiate_login(provider):
    """Return OAuth URL instead of redirecting immediately - for frontend-controlled flow"""
    try:
        logger.info(f"🔑 Login initiation requested for provider: {provider}")
        
        if provider == 'google':
            # Generate Google OAuth URL using existing flow configuration
            if not flow:
                logger.error("❌ OAuth flow not initialized")
                return jsonify({'error': 'OAuth not configured', 'success': False}), 500
            
            # Create a new flow instance with the correct redirect URI for the new callback
            from google_auth_oauthlib.flow import Flow
            from config.settings import SCOPES
            
            # Set up redirect URI for new callback endpoint
            if config.DEVELOPMENT_MODE:
                new_redirect_uri = "http://localhost:5000/api/auth/callback/google"
            else:
                new_redirect_uri = "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net/api/auth/callback/google"
            
            oauth_config = {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uris": [new_redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            }
            
            new_flow = Flow.from_client_config(oauth_config, scopes=SCOPES)
            new_flow.redirect_uri = new_redirect_uri
            
            # Generate authorization URL with state for security
            authorization_url, state = new_flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )
            
            # Store state and flow in session for verification
            session['oauth_state'] = state
            session['oauth_flow_redirect'] = new_redirect_uri
            logger.info(f"🔗 Generated Google OAuth URL with state: {state[:10]}...")
            
            return jsonify({
                'auth_url': authorization_url,
                'success': True,
                'provider': 'google',
                'state': state
            })
            
        else:
            logger.warning(f"⚠️ Unsupported OAuth provider: {provider}. Only 'google' is supported.")
            return jsonify({'error': f'Only Google OAuth is supported. Provider "{provider}" is not available.', 'success': False}), 400
            
    except Exception as e:
        logger.error(f"❌ Error initiating login for {provider}: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'success': False}), 500

def exchange_code_for_user_data(provider, code):
    """Helper function to exchange authorization code for user data"""
    try:
        if provider == 'google':
            # Create a new flow instance for token exchange
            from google_auth_oauthlib.flow import Flow
            from config.settings import SCOPES
            
            # Get the redirect URI from session or construct it
            redirect_uri = session.get('oauth_flow_redirect')
            if not redirect_uri:
                if config.DEVELOPMENT_MODE:
                    redirect_uri = "http://localhost:5000/api/auth/callback/google"
                else:
                    redirect_uri = "https://teacherfy-gma6hncme7cpghda.westus-01.azurewebsites.net/api/auth/callback/google"
            
            oauth_config = {
                "web": {
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                }
            }
            
            token_flow = Flow.from_client_config(oauth_config, scopes=SCOPES)
            token_flow.redirect_uri = redirect_uri
            
            # Set up the authorization response URL
            callback_url = f"{redirect_uri}?code={code}"
            
            # Exchange code for token
            token_flow.fetch_token(authorization_response=callback_url)
            credentials = token_flow.credentials
            
            # Verify token and get user info
            id_info = id_token.verify_oauth2_token(
                credentials.id_token,
                google_requests.Request(),
                CLIENT_ID,
                clock_skew_in_seconds=300
            )
            
            return {
                'id': id_info.get('sub'),
                'email': id_info.get('email'),
                'name': id_info.get('name', ''),
                'picture': id_info.get('picture', ''),
                'provider': 'google'
            }
            
        else:
            raise Exception(f"Unsupported provider: {provider}")
            
    except Exception as e:
        logger.error(f"❌ Error exchanging code for user data ({provider}): {e}")
        raise

@auth_blueprint.route('/api/auth/callback/<provider>', methods=['GET'])
def oauth_callback(provider):
    """Handle OAuth callback and redirect back to frontend"""
    try:
        logger.info(f"🔐 OAuth callback received for provider: {provider}")
        
        # Get authorization code from query params
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            logger.error(f"❌ OAuth error in callback: {error}")
            return redirect(f'http://localhost:3000/?auth=error&error={error}')
        
        if not code:
            logger.error("❌ No authorization code received")
            return redirect('http://localhost:3000/?auth=error&error=no_code')
        
        # Exchange code for user data
        try:
            user_data = exchange_code_for_user_data(provider, code)
            logger.info(f"✅ Successfully exchanged code for user data: {user_data.get('email')}")
        except Exception as exchange_error:
            logger.error(f"❌ Failed to exchange code for user data: {exchange_error}")
            return redirect('http://localhost:3000/?auth=error&error=exchange_failed')
        
        # Create user session
        session.permanent = True
        session['user_id'] = None  # Will update after database operation
        session['user_email'] = user_data['email']
        session['user_name'] = user_data.get('name', '')
        session['user_picture'] = user_data.get('picture', '')
        session['user_provider'] = provider
        session['is_premium'] = False
        
        # Store user info for backward compatibility
        session['user_info'] = {
            'email': user_data['email'],
            'name': user_data.get('name', ''),
            'picture': user_data.get('picture', ''),
            'provider': provider
        }
        
        logger.info("💾 User session created")
        
        # Create/update user in database
        user_id = None
        try:
            user_id = create_user(user_data['email'], user_data.get('name', ''), user_data.get('picture', ''))
            
            if user_id:
                try:
                    from core.database.database import get_db_cursor
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
        
        # Update user_id in session after successful database operation
        if user_id:
            session['user_id'] = user_id
            logger.info(f"✅ Updated session with user_id: {user_id}")
        
        logger.info(f"✅ Successfully authenticated user: {user_data['email']} via {provider}")
        
        # Redirect back to frontend with success
        frontend_url = 'http://localhost:3000' if config.DEVELOPMENT_MODE else 'https://teacherfy.ai'
        return redirect(f'{frontend_url}/?auth=success&provider={provider}')
        
    except Exception as e:
        logger.error(f"❌ OAuth callback error for {provider}: {e}")
        logger.error(traceback.format_exc())
        frontend_url = 'http://localhost:3000' if config.DEVELOPMENT_MODE else 'https://teacherfy.ai'
        return redirect(f'{frontend_url}/?auth=error&error=callback_failed')

# EXISTING OAUTH ENDPOINTS (keeping for backward compatibility)

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

        # Store user data in session for persistence
        session.permanent = True
        session['user_id'] = None  # Will update after database operation
        session['user_email'] = id_info['email']
        session['user_name'] = id_info.get('name', '')
        session['user_picture'] = id_info.get('picture', '')
        session['is_premium'] = False
        session['login_time'] = id_info.get('iat')
        
        # Store minimal user info for backward compatibility
        user_info = {
            'email': id_info['email'],
            'name': id_info.get('name', ''),
            'picture': id_info.get('picture', '')
        }
        session['user_info'] = user_info
        logger.info("💾 User info stored in session")

        # Create/update user in database
        user_id = None
        try:
            user_id = create_user(user_info['email'], user_info['name'], user_info['picture'])
            
            if user_id:
                try:
                    from core.database.database import get_db_cursor
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
        
        # Update user_id in session after successful database operation
        if user_id:
            session['user_id'] = user_id
            logger.info(f"✅ Updated session with user_id: {user_id}")
        
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
        user_email = session.get('user_email') or session.get('user_info', {}).get('email', 'Unknown')
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