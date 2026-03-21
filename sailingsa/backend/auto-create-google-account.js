#!/usr/bin/env node
// Automated Google Account Creation for sailingsa.co.za

const { exec } = require('child_process');
const readline = require('readline');

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

console.log('\n🔐 Automated Google Account Creation for sailingsa.co.za\n');
console.log('Opening Google signup page...\n');

// Open Google signup
const signupUrl = 'https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp';
exec(`open "${signupUrl}"`, () => {
  console.log('📋 FORM DETAILS TO ENTER:\n');
  console.log('First name: SailingSA');
  console.log('Last name: Admin');
  console.log('Username: admin@sailingsa.co.za');
  console.log('   (or try: hello@sailingsa.co.za, info@sailingsa.co.za)');
  console.log('Password: (create strong password)\n');
  
  console.log('⚠️  IMPORTANT:');
  console.log('   - You need access to sailingsa.co.za email to verify');
  console.log('   - Complete CAPTCHA manually');
  console.log('   - Verify email when prompted\n');
  
  console.log('After account is created, press Enter to continue setup...');
  
  rl.question('\nPress Enter when Google account is created: ', () => {
    console.log('\n✅ Now run: npm run setup-google');
    console.log('   This will configure OAuth with your new account\n');
    rl.close();
  });
});
