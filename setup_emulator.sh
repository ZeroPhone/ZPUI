touch emulator
cat << EOF > config.json
{"input":[{"driver":"pygame_input"}],"output":[{"driver":"pygame_emulator"}]}
EOF
touch apps/phone/do_not_load #Phone app will try to connect to modem, emulator environment is unlikely to have one
touch apps/hardware_apps/do_not_load #Currently, the only hardware app is ZeroPhone-specific
touch apps/flashlight/do_not_load #Flashlight app depends on ZeroPhone hardware
#In future, modem could be emulated - until that, the app will likely have to be disabled on emulators
