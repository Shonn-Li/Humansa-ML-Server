#!/usr/bin/env python3
"""
Script to integrate the conversation API into the main application
Adds the necessary imports and initialization to src/main.py
"""

import os
import sys

def integrate_conversation_api():
    """Add conversation API integration code"""
    
    # Integration code to be added to main.py
    integration_code = '''
# Humansa V2 Conversation API
from src.humansa.v2.api_conversation import humansa_v2_conversation_bp, initialize_v2_conversation_system

# Register V2 conversation blueprint
app.register_blueprint(humansa_v2_conversation_bp)

# Initialize V2 conversation system after database is ready
@app.before_serving
async def init_v2_conversation():
    """Initialize V2 conversation system"""
    try:
        await initialize_v2_conversation_system(
            db_pool=app.db_pool,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        logger.info("✅ Humansa V2 Conversation API initialized")
    except Exception as e:
        logger.error(f"Failed to initialize V2 conversation API: {e}")
'''

    print("📝 Integration Instructions for Conversation API")
    print("=" * 50)
    print()
    print("Add the following to src/main.py:")
    print()
    print("1. Add import near other Humansa imports:")
    print("   from src.humansa.v2.api_conversation import humansa_v2_conversation_bp, initialize_v2_conversation_system")
    print()
    print("2. Register blueprint after other blueprints:")
    print("   app.register_blueprint(humansa_v2_conversation_bp)")
    print()
    print("3. Add initialization in startup (after DB is ready):")
    print("   await initialize_v2_conversation_system(db_pool, openai_api_key)")
    print()
    print("New API Endpoints:")
    print("- POST /v2/humansa/conversations - Create new conversation")
    print("- POST /v2/humansa/conversations/<id>/messages - Add message")
    print("- GET  /v2/humansa/conversations/<id> - Get conversation")
    print("- POST /v2/humansa/conversations/<id>/stream - Stream response")
    print("- POST /v2/humansa/conversations/<id>/compress - Compress context")
    print("- POST /v2/humansa/conversations/cleanup - Clean old conversations")
    print()
    print("Test with: python test_conversation_api.py")
    print()
    
    # Create a patch file for easier application
    patch_content = '''--- a/src/main.py
+++ b/src/main.py
@@ -XX,X +XX,X @@ from src.humansa.api import humansa_bp
 from src.humansa.v2.api import humansa_v2_bp
+from src.humansa.v2.api_conversation import humansa_v2_conversation_bp, initialize_v2_conversation_system
 
@@ -XX,X +XX,X @@ app.register_blueprint(humansa_bp)
 app.register_blueprint(humansa_v2_bp)
+app.register_blueprint(humansa_v2_conversation_bp)
 
@@ -XX,X +XX,X @@ async def startup():
     # Initialize Humansa V2
     await initialize_v2_system(app.db_pool, openai_api_key)
+    
+    # Initialize V2 Conversation API
+    await initialize_v2_conversation_system(app.db_pool, openai_api_key)
'''
    
    with open('conversation_api_integration.patch', 'w') as f:
        f.write(patch_content)
    
    print("Patch file created: conversation_api_integration.patch")
    print("Apply manually to src/main.py at the appropriate locations")

if __name__ == "__main__":
    integrate_conversation_api()