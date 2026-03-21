// Quick Google OAuth Setup Helper
const readline = require('readline');
const fs = require('fs');
const { exec } = require('child_process');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('🔐 Google OAuth Quick Setup\n');
console.log('Opening Google Cloud Console...');
exec('open "https://console.cloud.google.com/apis/credentials?project=_"');

console.log('\n📋 Quick Steps:');
console.log('1. Click "Create Credentials" → "OAuth client ID"');
console.log('2. Application type: Web application');
console.log('3. Name: SailingSA Local');
console.log('4. Authorized redirect URIs: http://localhost:3001/auth/google/callback');
console.log('5. Click Create');
console.log('\nAfter creating, paste your credentials below:\n');

rl.question('Client ID: ', (clientId) => {
  rl.question('Client Secret: ', (clientSecret) => {
    const envContent = `PORT=3001
FRONTEND_URL=http://localhost:8080

GOOGLE_CLIENT_ID=${clientId}
GOOGLE_CLIENT_SECRET=${clientSecret}
GOOGLE_CALLBACK_URL=http://localhost:3001/auth/google/callback

SESSION_SECRET=${require('crypto').randomBytes(32).toString('hex')}
`;

    fs.writeFileSync('.env.local', envContent);
    console.log('\n✅ Saved to .env.local');
    console.log('\nRestart backend to apply changes.');
    rl.close();
  });
});
