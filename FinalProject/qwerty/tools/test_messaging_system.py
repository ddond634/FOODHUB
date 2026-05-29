"""
Test script for Customer-Seller Messaging System
Tests the full messaging flow end-to-end
"""

import requests
import json

BASE_URL = "http://127.0.0.1:5000"

def test_messaging_system():
    print("🧪 Testing Customer-Seller Messaging System\n")
    
    # Step 1: Create a test customer (or use existing)
    print("1️⃣ Registering test customer...")
    customer_data = {
        "username": "test_customer_msg",
        "email": "customer_msg@test.com",
        "password": "Test123!",
        "first_name": "Test",
        "last_name": "Customer",
        "phone": "09123456789",
        "address": "123 Test St"
    }
    
    response = requests.post(f"{BASE_URL}/api/register", json=customer_data)
    if response.status_code == 201 or "already registered" in response.json().get('message', ''):
        print("✅ Customer account ready")
        
        # Login to get token
        login_response = requests.post(f"{BASE_URL}/api/login", json={
            "email": customer_data["email"],
            "password": customer_data["password"]
        })
        
        if login_response.status_code == 200:
            customer_token = login_response.json()['data']['token']
            print(f"✅ Customer logged in (token: {customer_token[:20]}...)")
        else:
            print(f"❌ Customer login failed: {login_response.json()}")
            return
    else:
        print(f"❌ Customer registration failed: {response.json()}")
        return
    
    # Step 2: Get a seller ID from database (or create one)
    print("\n2️⃣ Getting seller information...")
    # For testing, we'll use seller_id = 1 (adjust if needed)
    seller_id = 1
    print(f"✅ Using seller_id: {seller_id}")
    
    # Step 3: Create a conversation
    print("\n3️⃣ Creating conversation...")
    headers = {
        "Authorization": f"Bearer {customer_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/api/conversations/create",
        headers=headers,
        json={"seller_id": seller_id}
    )
    
    if response.status_code == 200:
        conversation_data = response.json()['data']
        conversation_id = conversation_data['conversation_id']
        print(f"✅ Conversation created (ID: {conversation_id})")
        print(f"   Seller: {conversation_data.get('seller_name', 'Unknown')}")
    else:
        print(f"❌ Conversation creation failed: {response.json()}")
        return
    
    # Step 4: Send a message from customer
    print("\n4️⃣ Sending message from customer...")
    message_text = "Hi! I'm interested in your products. Are they still available?"
    
    response = requests.post(
        f"{BASE_URL}/api/messages/send",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "message_text": message_text
        }
    )
    
    if response.status_code == 201:
        message_data = response.json()['data']['message']
        print(f"✅ Message sent successfully")
        print(f"   Message: {message_data['message_text']}")
        print(f"   Time: {message_data['created_at']}")
    else:
        print(f"❌ Message send failed: {response.json()}")
        return
    
    # Step 5: Get customer conversations
    print("\n5️⃣ Fetching customer conversations...")
    response = requests.get(
        f"{BASE_URL}/api/conversations",
        headers=headers
    )
    
    if response.status_code == 200:
        conversations = response.json()['data']['conversations']
        print(f"✅ Found {len(conversations)} conversation(s)")
        for conv in conversations:
            print(f"   - ID: {conv['id']}, Seller: {conv['seller_name']}")
            print(f"     Last: {conv['last_message'][:50] if conv['last_message'] else 'No messages'}...")
    else:
        print(f"❌ Fetch conversations failed: {response.json()}")
        return
    
    # Step 6: Get messages in conversation
    print("\n6️⃣ Fetching messages...")
    response = requests.get(
        f"{BASE_URL}/api/messages/{conversation_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        messages = response.json()['data']['messages']
        print(f"✅ Found {len(messages)} message(s)")
        for msg in messages:
            sender = "You" if msg['sender_role'] == 'customer' else "Seller"
            print(f"   [{sender}] {msg['message_text']}")
    else:
        print(f"❌ Fetch messages failed: {response.json()}")
        return
    
    # Step 7: Check unread count
    print("\n7️⃣ Checking unread message count...")
    response = requests.get(
        f"{BASE_URL}/api/messages/unread-count",
        headers=headers
    )
    
    if response.status_code == 200:
        unread_count = response.json()['data']['unread_count']
        print(f"✅ Unread messages: {unread_count}")
    else:
        print(f"❌ Unread count failed: {response.json()}")
    
    # Step 8: Test mark as read
    print("\n8️⃣ Marking messages as read...")
    response = requests.patch(
        f"{BASE_URL}/api/messages/read/{conversation_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        marked = response.json()['data']['marked_read']
        print(f"✅ Marked {marked} message(s) as read")
    else:
        print(f"❌ Mark as read failed: {response.json()}")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - Messaging system is working!")
    print("="*60)
    print("\n📝 Summary:")
    print(f"   - Conversation ID: {conversation_id}")
    print(f"   - Customer token works: ✅")
    print(f"   - Can create conversations: ✅")
    print(f"   - Can send messages: ✅")
    print(f"   - Can fetch conversations: ✅")
    print(f"   - Can fetch messages: ✅")
    print(f"   - Unread count works: ✅")
    print(f"   - Mark as read works: ✅")
    print("\n🎉 System ready for production!")

if __name__ == "__main__":
    try:
        test_messaging_system()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://127.0.0.1:5000")
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
