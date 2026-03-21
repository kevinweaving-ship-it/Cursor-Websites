#!/usr/bin/env node
// Google OAuth Setup - Using TimAdvisor Google Account

const { exec } = require('child_process');
const readline = require('readline');
const fs = require('fs');
const path = require('path');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('\n🔐 Google OAuth Setup - TimAdvisor Account\n');
console.log('⚠️  IMPORTANT: Use TimAdvisor Google account, not personal!\n');

// Open the Google Auth Platform branding page
const projectId = 'all-tims-regatta-and-stats';
const brandingUrl = `https://console.cloud.google.com/auth/branding?project=${projectId}`;

exec(`open "${brandingUrl}"`, () => {
  console.log('📋 FOLLOW THESE STEPS:\n');
  console.log('1. Make sure you\'re logged into the TIMADVISOR Google account');
  console.log('   (Not your personal kevinweaving@gmail.com account)\n');
  
  console.log('2. On the page that opened, click "Get started"');
  console.log('3. Configure your app:');
  console.log('   - App name: SailingSA Results');
  console.log('   - Support email: timadvisor@... (use TimAdvisor email)');
  console.log('   - Click "Save"\n');
  
  console.log('4. Go to "Clients" in the left menu');
  console.log('5. Click "Create client"');
  console.log('6. Select "Web application"');
  console.log('7. Name: SailingSA');
  console.log('8. Add Authorized redirect URIs:');
  console.log('   * http://localhost:3001/auth/google/callback');
  console.log('   * https://sailingsa.co.za/auth/google/callback');
  console.log('9. Click "Create"\n');
  
  console.log('10. Copy your credentials and paste below:\n');
  
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
        console.log('✅ Using TimAdvisor Google account');
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
                    console.log('\n🎉 Setup complete using TimAdvisor account!');
                    console.log('\n📝 Test it now:');
                    console.log('   http://localhost:8080/timadvisor/login.html');
                    console.log('\n📊 Backend logs:');
                    console.log('   tail -f ' + backendLog);
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
