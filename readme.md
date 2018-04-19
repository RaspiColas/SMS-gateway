There are the Python programs for a Raspberry Pi Zero and NadHat daughter board for monitoring and controlling via SMS a set of remote temperature and power sensors. These sensors might be other Raspberries with DHT-22 sensor and other SMS modem, or RTU-5023 all included devices.

Main programs are:
- "multisonde.py" : Main program for controlling the sensors and responding to requests on their status. Could be started at boot time via crontab.
- "check_multisonde.py" : Program to be run regularly (e.g., every hour via crontab) to check if multisonde.py is still alive and do some housekeeping
- "stop_multisonde.py" : Program to stop nicely multisonde.py program

Requires:
- A file of sensor data (sensor name, sensor tel number, administrator tel number): multi_location_data.txt
- A configuration file: monitor_sms.conf including:
	send_email, pass_email [for sending email via gmail], 
	SMS_FREE [SMS server number], 
	tel_admin [overall administrator tel number], 
	add_admin [overall administrator tel email]

Creates:
- A general log file log_multisonde.log (and potentially older contents in log_multisonde_YYMMDD.log)
- An SMS in log file sms_in.log (and potentially older contents in sms_in_YYMMDD.log)
- An SMS out log file sms_out.log (and potentially older contents in sms_out_YYMMDD.log)
- An errors log file log_err_multisonde.log (and potentially older contents in log_multisonde_YYMMDD.log)
- A CSV file of data for each sensor :[name_sensor]_data.txt
- A png file of the data graphic for each sensor : [name_sensor]_plot.png
- A temporary boot file time_boot.txt to detect fast reboot loops

