#!/usr/bin/env node
// Automated Google OAuth Client ID Creation Helper

const { exec } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('\n🔐 Google OAuth Setup - Automated\n');
console.log('Opening Google Cloud Console to create OAuth Client ID...\n');

// Open the exact OAuth client creation page
const projectId = 'all-tims-regatta-and-stats';
const createUrl = `https://console.cloud.google.com/apis/credentials/consent/edit?project=${projectId}`;

exec(`open "${createUrl}"`, () => {
  console.log('📋 STEP-BY-STEP INSTRUCTIONS:\n');
  console.log('1. First, configure OAuth Consent Screen:');
  console.log('   - User type: External');
  console.log('   - App name: SailingSA Results');
  console.log('   - Support email: (your email)');
  console.log('   - Scopes: Add "openid", "email", "profile"');
  console.log('   - Click "Save and Continue" through all steps\n');
  
  console.log('2. Then go to Credentials page:');
  console.log('   - Click "Create Credentials" → "OAuth client ID"');
  console.log('   - Application type: Web application');
  console.log('   - Name: SailingSA');
  console.log('   - Authorized redirect URIs:');
  console.log('     * http://localhost:3001/auth/google/callback');
  console.log('     * https://sailingsa.co.za/auth/google/callback');
  console.log('   - Click "Create"\n');
  
  console.log('3. Copy your credentials and paste them below:\n');
  
  setTimeout(() => {
    rl.question('📋 Client ID (ends with .apps.googleusercontent.com): ', (clientId) => {
      if (!clientId || !clientId.includes('.apps.googleusercontent.com')) {
        console.log('\n❌ Invalid Client ID format. Please try again.');
        rl.close();
        process.exit(1);
      }
      
      rl.question('🔑 Client Secret: ', (clientSecret) => {
        if (!clientSecret || clientSecret.length < 10) {
          console.log('\n❌ Invalid Client Secret. Please try again.');
          rl.close();
          process.exit(1);
        }
        
        // Generate session secret
        const crypto = require('crypto');
        const sessionSecret = crypto.randomBytes(32).toString('hex');
        
        // Create .env.local content
        const envContent = `PORT=3001
FRONTEND_URL=http://localhost:8080

GOOGLE_CLIENT_ID=${clientId.trim()}
GOOGLE_CLIENT_SECRET=${clientSecret.trim()}
GOOGLE_CALLBACK_URL=http://localhost:3001/auth/google/callback

SESSION_SECRET=${sessionSecret}
`;

        // Write to .env.local
        const envPath = path.join(__dirname, '.env.local');
        fs.writeFileSync(envPath, envContent);
        
        console.log('\n✅ Credentials saved to .env.local');
        console.log('✅ Session secret generated');
        console.log('\n🔄 Restarting backend...\n');
        
        // Kill existing backend
        exec('pkill -f "node server.js"', () => {
          // Start backend
          const backendPath = path.join(__dirname, 'server.js');
          const backendProcess = exec(`node "${backendPath}"`, (error) => {
            if (error) {
              console.error('❌ Error starting backend:', error.message);
            }
          });
          
          backendProcess.stdout.on('data', (data) => {
            if (data.includes('Google OAuth configured')) {
              console.log('✅ Backend started with Google OAuth configured!');
              console.log('\n🎉 Setup complete! Test it:');
              console.log('   http://localhost:8080/timadvisor/login.html');
              console.log('\nPress Ctrl+C to stop backend\n');
            }
          });
          
          setTimeout(() => {
            console.log('✅ Backend process started (PID:', backendProcess.pid + ')');
            console.log('   Check logs: tail -f /tmp/sailingsa-backend.log\n');
          }, 2000);
        });
        
        rl.close();
      });
    });
  }, 2000);
});
