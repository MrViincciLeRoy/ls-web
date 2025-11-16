import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "test_key"
API_SECRET = "test_secret"

headers = {
    "Authorization": f"token {API_KEY}:{API_SECRET}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# Sample transactions to upload
transactions = [
    {
        "transaction_id": "TXN001",
        "amount": 1500.00,
        "currency": "USD",
        "customer": "Customer A",
        "date": "2025-11-16",
        "status": "Completed"
    },
    {
        "transaction_id": "TXN002",
        "amount": 2300.50,
        "currency": "USD",
        "customer": "Customer B",
        "date": "2025-11-16",
        "status": "Pending"
    },
    {
        "transaction_id": "TXN003",
        "amount": 850.75,
        "currency": "EUR",
        "customer": "Customer C",
        "date": "2025-11-15",
        "status": "Completed"
    }
]

def upload_transactions():
    print("Uploading transactions...")
    
    for txn in transactions:
        response = requests.post(
            f"{BASE_URL}/api/resource/Transaction",
            headers=headers,
            json=txn
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Uploaded {txn['transaction_id']}: {result['data']['name']}")
        else:
            print(f"✗ Failed to upload {txn['transaction_id']}: {response.text}")

def list_transactions():
    print("\nListing all transactions...")
    
    response = requests.get(
        f"{BASE_URL}/api/resource/Transaction",
        headers=headers,
        params={
            "fields": json.dumps(["name", "transaction_id", "amount", "status"]),
            "limit": 100
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Found {len(result['data'])} transactions:")
        for txn in result['data']:
            print(f"  - {txn['transaction_id']}: ${txn['amount']} ({txn['status']})")
    else:
        print(f"Failed to list transactions: {response.text}")

def get_transaction(name):
    print(f"\nGetting transaction {name}...")
    
    response = requests.get(
        f"{BASE_URL}/api/resource/Transaction/{name}",
        headers=headers
    )
    
    if response.status_code == 200:
        result = response.json()
        print(json.dumps(result['data'], indent=2))
    else:
        print(f"Failed to get transaction: {response.text}")

if __name__ == "__main__":
    upload_transactions()
    list_transactions()
