-- AppleScript to automate Google Account creation
tell application "Google Chrome"
	activate
	delay 2
end tell

tell application "System Events"
	tell process "Google Chrome"
		set frontmost to true
		delay 1
		
		-- Fill first name
		keystroke "SailingSA"
		delay 0.5
		keystroke tab
		
		-- Fill last name
		delay 0.5
		keystroke "Admin"
		delay 0.5
		keystroke tab
		
		-- Fill username/email
		delay 0.5
		keystroke "admin@sailingsa.co.za"
		delay 0.5
		keystroke tab
		
		-- Fill password (will need user to complete)
		delay 0.5
		keystroke tab
	end tell
end tell
