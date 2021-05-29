#!/usr/bin/env python3
# This script is meant to run indefenitly upon startup of a computer.
# 
from __future__ import print_function # Python 2/3 compatibility
import json
import decimal # noSQL database requires floating point data to be converted into decimals
from decimal import Decimal
import bme680 		#Module for first sensor board
import datetime 	#Allows me to capture date time, note that some computers such as the raspi pi W dont have good clocks, ensure wifi is up for accurate time
import time
from time import sleep
import os 			# Not sure this is required
import vcgencmd 	# Module for CPU temp --> Not working currently for some reason I think it mihht be dues to python versions
import subprocess
from subprocess import call
import smtplib
from email.mime.text import MIMEText
import RPi.GPIO as GPIO
import smbus
import csv
import psutil
from gpiozero import CPUTemperature
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.mime.base import MIMEBase
import statistics

def get_computer_status():
	#!/usr/bin/env python
	# gives a single float value
	psutil.cpu_percent()
	# gives an object with many fields
	psutil.virtual_memory()
	
	# you can convert that object to a dictionary 
	dict(psutil.virtual_memory()._asdict())
	# you can have the percentage of used RAM
	psutil.virtual_memory().percent
	# you can calculate percentage of available memory
	
	computer_stats = {
		'Computer temp (C)': 	CPUTemperature().temperature,
		'Memory Remaining': 	psutil.virtual_memory().available * 100 / psutil.virtual_memory().total,
		'Disk Usange': 			str(psutil.disk_usage('/'))
	}
	# Pretty Print JSON
	json_formatted_str = json.dumps(computer_stats, indent=4)
	return json_formatted_str

def process_data_from_file(filename='./DATA25-05-2021-23-57-14.csv'):
	try:
		data_dict = {}
		for i in range(6):
			data_dict[i] = ([],[])
		with open(filename, 'r') as fp:
			for i in fp.read().split('\n'):
				if i == '': continue
				splitted = i.split(',')
				tca = splitted[0]
				# print(data_dict[int(tca)])
				data_dict[int(tca)][0].append(float(splitted[4])) # RH
				data_dict[int(tca)][1].append(float(splitted[3])) # T
		string_builder = ''
		for i in range(6):
			RH = data_dict[int(i)][0]
			T = data_dict[int(i)][1]
			string_builder += '%i: RH (Percent) --> %s +/- %s. Min %s, Max %s \n'%(i, round(statistics.mean(RH),2), round(statistics.stdev(RH),3), str(min(RH)),  str(max(RH)))
			string_builder += '%i: T (C) 		--> %s +/- %s. Min %s, Max %s \n'%(i, round(statistics.mean(T), 2), round(statistics.stdev(T),3), str(min(T)), str(max(T)))
		return string_builder
	except:
		return "None"

# For testing purposes
# print(process_data_from_file())
# assert 1 ==2

class multiplex:
	"""
	Multiplexer class used to interface with TCA4548A
	https://www.ti.com/lit/ds/symlink/tca9548a.pdf
	"""
	def __init__(self, bus):
		self.bus = smbus.SMBus(bus)

	def channel(self, address=0x70,channel=0):  # values 0-3 indictae the channel, anything else (eg -1) turns off all channels
		if   (channel==0): action = 1
		elif (channel==1): action = 2
		elif (channel==2): action = 4
		elif (channel==3): action = 8
		elif (channel==4): action = 16
		elif (channel==5): action = 32
		elif (channel==6): action = 64
		elif (channel==7): action = 128
		else : action = 0x00
		self.bus.write_byte_data(address,0x04,action)  #0x04 is the register for switching channels

def email(message, body='Loggin...'):
	try:
		# Change to your own account information
		# Account Information
		to = 'EMAIL0, EMAIL1' # Email to send to.
		gmail_user = 'tristan.chauvinbosse@gmail.com' # Email to send from. (MUST BE GMAIL)
		gmail_password = 'MYPASSWORD' # Gmail password.
		smtpserver = smtplib.SMTP('smtp.gmail.com', 587) # Server to use.
		smtpserver.ehlo()  # Says 'hello' to the server
		smtpserver.starttls()  # Start TLS encryption
		smtpserver.ehlo()
		smtpserver.login(gmail_user, gmail_password)  # Log in to server
		today = datetime.date.today()  # Get current time/date

		# Creates the text, subject, 'from', and 'to' of the message.
		msg = MIMEText(body)
		msg['Subject'] = message
		msg['From'] = gmail_user
		msg['To'] = to
		# Sends the message
		smtpserver.sendmail(gmail_user, to.split(','), msg.as_string())
		# Closes the smtp server.
		smtpserver.quit()
	except:
		print("Message Failed to send")


if __name__ == '__main__':
	# Initialize gpios and sets the GPIO we will be useing to trigger the I2C's reset
	pwr = 15
	GPIO.cleanup()
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(pwr, GPIO.OUT)  

	# Multiplexer and sensors
	bus=1       				# 0 for rev1 boards etc. 
	address=0x70				# This multiplexer has address 0x70
	plexer = multiplex(bus)		# Initilizes the object which will be used to switch channels on the multiplexer.
	tcas = [0,1,2,3,4,5]		# All the sensors are connected to these channels on the multiplexer

	# Formatting file name
	dt_string = datetime.datetime.today().strftime("%d-%m-%Y-%H-%M-%S")
	absolute_file_path = '/home/pi/DATA%s.txt'%(dt_string)
	print(dt_string)

	# Couters and vars
	booted = False					# Email on script startup.
	multiplexer_resettime = 0.001 	# Must be lower than 0.000001 seconds, this value can practically be set to zero.
	watchdog_timer = 5				# Emails data everyso often.
	loops = 0						# A counter to compare to watchdog.
	sleeptime = 60 					# Loosely corresponds to time in between measurements. We rely on wifi clock for accuracy on this. 600 worked well during testing.

	with open(absolute_file_path, 'w') as f: 
		while True:
			print("\n ################")
			working_sensors = []
			for tca in tcas: # Pools sensor for each one connected to multiplexer.
				time_before_sampling = datetime.datetime.now()
				# Triggers reset on multiplexer to avoid bus blocks?
				GPIO.output(pwr, GPIO.LOW) 
				time.sleep(multiplexer_resettime)
				GPIO.output(pwr, GPIO.HIGH)
				time.sleep(multiplexer_resettime)
				# Try sampling from sensor

				try:
					plexer.channel(address,99)
					sensor = None 	# Prevents measurement duplicates
					print(tca)		# Print out the sensor we are sampling these correspond to multiplexer channel
					plexer.channel(address,tca)	# Use created class to change multiplexer channels (this enables us to pool multiple BME680 sensors which have the same default I2C address)
					# If firstime boot log the I2C detect to nohup.
					if booted == False:
						call("sudo i2cdetect -y 1", shell=True)
					# 
					# time.sleep(1)

					# Uses class to interface with sensor (https://github.com/pimoroni/bme680-python)
					try:
						sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
					except:
						try:
							sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
						except Exception as e:
							print(e) 

					# Try to query sensor and if it succeeds we append the channel to a list for keeping track of the active ones.
					try:						
						sensor.get_sensor_data()
						Item={
							'date':                     str(datetime.datetime.now().date()),    # I used this as my key
							'identifier':				int(tca),
							'time':                     str(datetime.datetime.now().time()),    # Used this as my sort
							'Temperature (C)':   		Decimal('{0:.2f}'.format(sensor.data.temperature)),
							'Pressure (Pa)':            Decimal('{0:.2f}'.format(sensor.data.pressure)),
							'Gas Resistance (Ohms)':    Decimal('{0:.0f}'.format(sensor.data.gas_resistance)),
							'Humidity (%)':      		Decimal('{0:.2f}'.format(sensor.data.humidity)),
							}

						# Writes data to textfile.
						writer = csv.writer(f)
						writer.writerow([Item['identifier'], Item['date'], Item['time'], Item['Temperature (C)'], Item['Humidity (%)'], Item['Pressure (Pa)'], Item['Gas Resistance (Ohms)']])
						# If first time booted
						if booted == False:
							print(Item)
						# Success!
						working_sensors.append(str(tca))
						
					except Exception as e:
						print(e)
				except Exception as e:
					print(e)
			
			# Blinks and Emails when a sensor fails
			if len(working_sensors) != 6:
				for i in range(10):
					call("sudo echo 1 > /sys/class/leds/led0/brightness", shell=True)
					time.sleep(1)
					call("sudo echo 0 > /sys/class/leds/led0/brightness", shell=True)
				# email('Alert only %s are currently loggin, please check %s'%(len(working_sensors), str(working_sensors)))

			# If Sucesfully started logging with all six sensors
			elif len(working_sensors) == 6 and booted == False:
				email('Looging succefully started with filename: DATA%s'%(dt_string), body='Status: %s sensors are currently loggin %s'%(len(working_sensors), str(working_sensors)))
			
			booted = True
			loops += 1
			# Flushes buffered data to file
			f.flush()
			# Sends data via email
			if loops > watchdog_timer:
				with open(absolute_file_path, 'r') as fp:
					email('Status: %s sensors are currently loggin %s'%(len(working_sensors), str(working_sensors)), body = '%s\n%s\n%s'%(get_computer_status(),process_data_from_file(filename=absolute_file_path) ,str(fp.read())))
				# Reset watchdog timer
				loops = 0
			# Sleeps to sample measuremetns out
			time_delta = datetime.datetime.now() - time_before_sampling
			print('Sampling time %s'%(time_delta.total_seconds()))
			print('Sleeping for %d'%(sleeptime-time_delta.total_seconds()))
			time.sleep(sleeptime-time_delta.total_seconds())
