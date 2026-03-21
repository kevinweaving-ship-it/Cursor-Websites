#!/usr/bin/env node
// Google OAuth Setup - SailingSA.co.za Account

const { exec } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('\n🔐 Google OAuth Setup - SailingSA.co.za\n');
console.log('⚠️  IMPORTANT: Use a Google account for sailingsa.co.za\n');
console.log('   Option 1: Create new Google account (recommended)');
console.log('   Option 2: Use existing account with sailingsa.co.za email\n');

// Open the Google Auth Platform branding page
const projectId = 'all-tims-regatta-and-stats';
const brandingUrl = `https://console.cloud.google.com/auth/branding?project=${projectId}`;

exec(`open "${brandingUrl}"`, () => {
  console.log('📋 SETUP STEPS:\n');
  console.log('1. CREATE/LOGIN TO GOOGLE ACCOUNT FOR SAILINGSA.CO.ZA');
  console.log('   - Create new: https://accounts.google.com/signup');
  console.log('   - Use email like: admin@sailingsa.co.za or hello@sailingsa.co.za');
  console.log('   - OR use existing account that manages sailingsa.co.za\n');
  
  console.log('2. In Google Cloud Console (page that opened):');
  console.log('   - Make sure you\'re logged into the SAILINGSA account');
  console.log('   - Click "Get started"');
  console.log('   - Configure app:');
  console.log('     * App name: SailingSA Results');
  console.log('     * Support email: admin@sailingsa.co.za (or your sailingsa email)');
  console.log('     * Click "Save"\n');
  
  console.log('3. Go to "Clients" in left menu');
  console.log('4. Click "Create client"');
  console.log('5. Select "Web application"');
  console.log('6. Name: SailingSA');
  console.log('7. Add Authorized redirect URIs:');
  console.log('   * http://localhost:3001/auth/google/callback');
  console.log('   * https://sailingsa.co.za/auth/google/callback');
  console.log('8. Click "Create"\n');
  
  console.log('9. Copy credentials and paste below:\n');
  
  setTimeout(() => {
    rl.question('📋 Client ID (ends with .apps.googleusercontent.com): ', (clientId) => {
      if (!clientId || !clientId.includes('.apps.googleusercontent.com')) {
        console.log('\n❌ Invalid Client ID. Must end with .apps.googleusercontent.com');
        console.log('   Please check and try again.\n');
        rl.close();
        process.exit(1);
      }
      
      rl.question('🔑 Client Secret: ', (clientSecret) => {
        if (!clientSecret || clientSecret.length < 10) {
          console.log('\n❌ Invalid Client Secret. Please check and try again.\n');
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
        console.log('✅ Using SailingSA.co.za Google account');
        console.log('✅ Session secret generated');
        console.log('\n🔄 Restarting backend...\n');
        
        // Kill existing backend
        exec('pkill -f "node server.js"', () => {
          setTimeout(() => {
            // Start backend in background
            const backendPath = path.join(__dirname, 'server.js');
            const backendLog = '/tmp/sailingsa-backend.log';
            
            exec(`node "${backendPath}" > ${backendLog} 2>&1 &`, (error) => {
              if (error) {
                console.error('❌ Error:', error.message);
                return;
              }
              
              setTimeout(() => {
                // Check if backend started successfully
                try {
                  const logContent = fs.readFileSync(backendLog, 'utf8');
                  if (logContent.includes('Google OAuth configured')) {
                    console.log('✅ Backend started with Google OAuth configured!');
                    console.log('\n🎉 Setup complete using SailingSA.co.za account!');
                    console.log('\n📝 Test it now:');
                    console.log('   http://localhost:8080/timadvisor/login.html');
                    console.log('\n📊 Backend logs:');
                    console.log('   tail -f ' + backendLog);
                    console.log('\n💡 For production:');
                    console.log('   Use same Client ID, add redirect URI:');
                    console.log('   https://sailingsa.co.za/auth/google/callback');
                    console.log('\n');
                  } else if (logContent.includes('not configured')) {
                    console.log('⚠️  Backend started but Google OAuth not configured');
                    console.log('   Check logs:', backendLog);
                  } else {
                    console.log('✅ Backend process started');
                    console.log('   Check status: curl http://localhost:3001/health');
                    console.log('   Check logs:', backendLog);
                  }
                } catch (e) {
                  console.log('✅ Backend process started');
                  console.log('   Check logs:', backendLog);
                }
              }, 2000);
            });
          }, 1000);
        });
        
        rl.close();
      });
    });
  }, 2000);
});
