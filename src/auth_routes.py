# src/auth_routes.py - FIXED VERSION with better error handling and debugging
from flask import Blueprint, request, jsonify, redirect, url_for, session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import traceback
import json

from src.config import logger, flow, CLIENT_ID, config
from src.db import get_user_by_email, create_user, log_user_login, log_user_activity

auth_blueprint = Blueprint("auth_blueprint", __name__)

@auth_blueprint.route('/auth/check', methods=['GET'])
def check_auth():
    """Check if the user is authenticated and session is valid."""
    try:
        logger.info("🔍 DEBUG: /auth/check route called")
        logger.info(f"🔍 DEBUG: Session keys: {list(session.keys())}")
        
        # Check if we have user info in session (simplified approach)
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
                        "is_premium": False  # You can extend this based on your user tiers
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

# Enhanced OAuth callback for debugging - Add this to your auth_routes.py

@auth_blueprint.route('/oauth2callback')
def oauth2callback():
    """Handle Google OAuth callback with comprehensive debugging."""
    try:
        logger.info("🔐 OAuth callback received")
        logger.info(f"🔍 Request URL: {request.url}")
        logger.info(f"🔍 Request args: {dict(request.args)}")
        logger.info(f"🔍 Request method: {request.method}")
        logger.info(f"🔍 Request headers: {dict(request.headers)}")
        
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
                        } else {
                            setTimeout(() => {
                                window.location.href = '/';
                            }, 3000);
                        }
                    </script>
                </body>
                </html>
            """
        
        # Fetch the token
        try:
            logger.info("🔍 Attempting to fetch token...")
            flow.fetch_token(authorization_response=request.url)
            credentials = flow.credentials
            logger.info("✅ Token fetched successfully")
            logger.info(f"🔍 Token expires at: {credentials.expiry}")
        except Exception as token_error:
            logger.error(f"❌ Token fetch error: {token_error}")
            logger.error(traceback.format_exc())
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>Failed to fetch authentication token</p>
                    <p>Error: {str(token_error)}</p>
                    <script>
                        console.error('Token fetch error:', '{str(token_error)}');
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Failed to get authentication token: {str(token_error)}'
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
            logger.info(f"🔍 User info from token: {id_info}")
        except Exception as verify_error:
            logger.error(f"❌ Token verification error: {verify_error}")
            logger.error(traceback.format_exc())
            return f"""
                <html>
                <head><title>Authentication Error</title></head>
                <body>
                    <h2>Authentication Error</h2>
                    <p>Failed to verify authentication token</p>
                    <p>Error: {str(verify_error)}</p>
                    <script>
                        console.error('Token verification error:', '{str(verify_error)}');
                        if (window.opener) {{
                            window.opener.postMessage({{
                                type: 'AUTH_ERROR',
                                error: 'Failed to verify authentication token: {str(verify_error)}'
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

        # Store user info in session
        user_info = {
            'email': id_info['email'],
            'name': id_info.get('name', ''),
            'picture': id_info.get('picture', '')
        }
        session['user_info'] = user_info
        session.permanent = True  # Make session persistent
        logger.info("💾 User info stored in session")
        logger.info(f"🔍 Session keys after storing user info: {list(session.keys())}")

        # Create/update user in database and log login
        user_id = None
        try:
            logger.info(f"🔍 Creating/updating user in database: {user_info['email']}")
            user_result = create_user(user_info['email'], user_info['name'], user_info['picture'])
            
            if isinstance(user_result, int):
                user_id = user_result
            elif isinstance(user_result, dict) and 'id' in user_result:
                user_id = user_result['id']
            else:
                logger.warning("⚠️ Unexpected user creation result format")
                user_id = None
            
            if user_id:
                log_user_login(user_id)
                logger.info(f"✅ User login logged for ID: {user_id}")
                
                # Store user ID in session for easier access
                session['user_id'] = user_id
            else:
                logger.warning("⚠️ Could not get user ID for login logging")
                
        except Exception as db_error:
            logger.error(f"❌ Database error during OAuth: {db_error}")
            logger.error(traceback.format_exc())
            # Continue with OAuth even if DB logging fails - don't break the login
        
        logger.info(f"✅ Successfully authenticated user: {user_info['email']}")
        
        # Return success page with comprehensive messaging
        return f"""
            <html>
            <head>
                <title>Authentication Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
                    .success {{ color: green; }}
                    .info {{ color: blue; }}
                </style>
            </head>
            <body>
                <h2 class="success">✅ Authentication Successful!</h2>
                <p class="info">Welcome, {user_info.get('name', user_info['email'])}!</p>
                <p>This window will close automatically...</p>
                
                <script>
                    console.log('🎉 OAuth success! User authenticated:', {{
                        email: '{user_info['email']}',
                        name: '{user_info.get('name', '')}',
                        user_id: {user_id or 'null'}
                    }});
                    
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
                            
                            // Close after a short delay to ensure message is sent
                            setTimeout(() => {{
                                console.log('🔒 Closing OAuth popup...');
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
                        // Fallback - just redirect
                        setTimeout(() => {{
                            window.location.href = '/';
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
                <p>Error: {str(e)}</p>
                <script>
                    console.error('OAuth callback error:', '{str(e)}');
                    if (window.opener) {{
                        window.opener.postMessage({{
                            type: 'AUTH_ERROR',
                            error: 'Authentication failed: {str(e)}'
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
        
@auth_blueprint.route('/authorize')
def authorize():
    """Initiate Google OAuth with the proper redirect URI."""
    try:
        logger.info("🔐 Starting OAuth authorization")
        
        if not flow:
            logger.error("❌ OAuth flow not initialized")
            return jsonify({"error": "OAuth not configured"}), 500
            
        logger.info(f"🔍 Flow redirect URI: {flow.redirect_uri}")
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force consent screen to ensure we get refresh token
        )
        session['state'] = state
        logger.info(f"🔗 Redirecting to: {authorization_url}")
        
        return redirect(authorization_url)
    except Exception as e:
        logger.error(f"❌ Error during OAuth authorization: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

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

# Add a debug route to check session and OAuth config
@auth_blueprint.route('/debug/oauth')
def debug_oauth():
    """Debug route to check OAuth configuration."""
    try:
        return jsonify({
            "flow_initialized": flow is not None,
            "client_id_exists": bool(CLIENT_ID),
            "redirect_uri": flow.redirect_uri if flow else None,
            "scopes": flow.scopes if flow else None,
            "session_keys": list(session.keys()),
            "has_user_info": 'user_info' in session,
            "user_email": session.get('user_info', {}).get('email', 'No email'),
            "development_mode": config.DEVELOPMENT_MODE
        })
    except Exception as e:
        logger.error(f"❌ Debug OAuth error: {e}")
        return jsonify({"error": str(e)}), 500

@auth_blueprint.route('/debug/database')
def debug_database():
    """Debug route to test database operations."""
    try:
        from src.db.database import test_connection
        
        results = {
            "connection_test": test_connection()
        }
        
        # Try to get a test user
        try:
            test_user = get_user_by_email("test@example.com")
            results["test_user_query"] = "success"
            results["test_user_exists"] = test_user is not None
        except Exception as e:
            results["test_user_query"] = f"error: {str(e)}"
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"❌ Debug database error: {e}")
        return jsonify({"error": str(e)}), 500