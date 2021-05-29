#!/usr/bin/env python3
from __future__ import print_function # Python 2/3 compatibility

# This python scripts samples on loop and uploads data to Database.
import boto3 # Here we will use boto3 fuctionality to pu_item into noSQL dynamoDB

# In the future I might consider using google's services to store on drive

# import gspread
# from oauth2client.service_account import ServiceAccountCredentials

import json
import decimal # noSQL database requires floating point data to be converted into decimals
from decimal import Decimal
import bme680 #Module for first sensor board
import datetime #Allows me to capture date time
import time
import Adafruit_DHT #Module for second sensor
from time import sleep
import os # Not sure this is required
import vcgencmd # Module for CPU temp --> Not working currently for some reason I think it mihht be dues to python versions
import subprocess
from subprocess import call
import smtplib
from email.mime.text import MIMEText
import RPi.GPIO as GPIO
from si7021 import Si7021
import smbus

class multiplex:
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

def email(message):
	try:
		# Change to your own account information
		# Account Information
		to = 'tristan.chauvin-bosse@mail.mcgill.ca' # Email to send to.
		gmail_user = 'tristan.chauvinbosse@gmail.com' # Email to send from. (MUST BE GMAIL)
		gmail_password = 'bf2142master' # Gmail password.
		smtpserver = smtplib.SMTP('smtp.gmail.com', 587) # Server to use.

		smtpserver.ehlo()  # Says 'hello' to the server
		smtpserver.starttls()  # Start TLS encryption
		smtpserver.ehlo()
		smtpserver.login(gmail_user, gmail_password)  # Log in to server
		today = datetime.date.today()  # Get current time/date

		# Creates the text, subject, 'from', and 'to' of the message.
		msg = MIMEText('Ran to stop')
		msg['Subject'] = message
		msg['From'] = gmail_user
		msg['To'] = to
		# Sends the message
		smtpserver.sendmail(gmail_user, [to], msg.as_string())
		# Closes the smtp server.
		smtpserver.quit()
	except:
		print("Message Failed to send")

if __name__ == '__main__':
	pwr = 15
	GPIO.cleanup()
	GPIO.setmode(GPIO.BOARD)
	GPIO.setup(pwr, GPIO.OUT)  

	bus=1       	# 0 for rev1 boards etc. 

	GPIO.output(pwr, GPIO.LOW) 
	time.sleep(1)
	GPIO.output(pwr, GPIO.HIGH)
	time.sleep(1)

	address=0x70
	plexer = multiplex(bus)
	plexer.channel(address,99)
	plexer.channel(address,0)
	# tcas = [0,1,2,3,4,5]

	# tcas = [0,1,2,3,4,5,6,7]
	while 1 == 1: 
		print("\n\n\n\n\n\n\n ################")
		try:

			sensor = "NULL"  
			call("sudo i2cdetect -y 1", shell=True)
			try:
				sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)
			except:
				try:
					sensor = bme680.BME680(bme680.I2C_ADDR_SECONDARY)
				except Exception as e:
					print(e)
			try:						#Query sensor
				sensor.get_sensor_data()
				Item={
					'date':                     str(datetime.datetime.now().date()),    # I used this as my key
					'identifier':				str('TEST'),
					'time':                     str(datetime.datetime.now().time()),    # Used this as my sort
					'Temperature (C)':   		Decimal('{0:.2f}'.format(sensor.data.temperature)),
					'Pressure (Pa)':            Decimal('{0:.2f}'.format(sensor.data.pressure)),
					'Gas Resistance (Ohms)':    Decimal('{0:.0f}'.format(sensor.data.gas_resistance)),
					'Humidity (%)':      		Decimal('{0:.2f}'.format(sensor.data.humidity)),
				}
				print(Item)
			except Exception as e:
				print(e)
		except Exception as e:
			print(e)
		time.sleep(1)	
