# Auth-Gated App Testing Playbook (Emergent Google Auth)

## Step 1: Create Test User & Session
```
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({user_id: userId, email: 'test.user.' + Date.now() + '@example.com', name: 'Test User', picture: 'https://via.placeholder.com/150', created_at: new Date()});
db.user_sessions.insertOne({user_id: userId, session_token: sessionToken, expires_at: new Date(Date.now() + 7*24*60*60*1000), created_at: new Date()});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API
```
curl -X GET "$API_URL/api/auth/me" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X GET "$API_URL/api/my-scans" -H "Authorization: Bearer YOUR_SESSION_TOKEN"
curl -X POST "$API_URL/api/predict" -H "Authorization: Bearer YOUR_SESSION_TOKEN" -F "mri=@test.jpg;type=image/jpeg" -F "location=Mumbai"
```

## Step 3: Browser Testing
```python
await page.context.add_cookies([{
    "name": "session_token", "value": "YOUR_SESSION_TOKEN",
    "domain": "tumour-mri-check.preview.emergentagent.com", "path": "/",
    "httpOnly": True, "secure": True, "sameSite": "None"
}])
await page.goto("https://tumour-mri-check.preview.emergentagent.com/history")
```

## Checklist
- User document has user_id field (custom UUID)
- Session user_id matches user's user_id
- All queries use {"_id": 0}
- /api/auth/me returns user data
- /history shows the user's scans when signed in
- Callback detection uses useLocation().hash

## Clean test data
```
mongosh --eval "use('test_database'); db.users.deleteMany({email: /test\.user\./}); db.user_sessions.deleteMany({session_token: /test_session/});"
```
