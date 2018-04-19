#!/usr/bin/python
# -*- coding: utf-8 -*-

#---------------------------------------------------#
#													#
#				multisonde.py						#
#													#
#---------------------------------------------------#

""""

Version: 17/4/18

Programme Python destiné à gérer par SMS des capteurs RTU5023 ou d'autres sources à l'aide de la carte NadHAT


HISTORIQUE:
-----------

Au 30/1:
- Ajout d'envoi par socket des données sondes vers un Raspi secondaire

Au 7/2:
- Ajout d'envoi par socket des ordres de mise à jour d'argent de poche

Au 14/2:
- Ajout d'envoi par SMS des commandes de services pour MWC

Au 3/3:
- Ajout du suivi des stats sur le nombre d'erreurs
- Correction de bug de lecture du numéro des gestionnaires de sondes

Au 12/3:
- Ajout de l'envoi régulier de SMS d'aide aux gestionnaires de sondes
- Ajout de l'envoi de l'adresse IP locale

Au 13/3:
- Envoi des données par socket en mode asynchrone

Au 17/3:
- Ajout d'un journal spécifique pour enregistrer les erreurs

Au 8/4:
- Ajout d'un mode de correction des messages reçus incluant les lettres accentuées 'é', 'è' et 'à'
- Ajout du traitement des alerts "Higher"
- Alerte radiateur oublié retirée pour l'été

Au 17/4:
- Ajout d'envoi de messages accentués !
- Ajout de l'interprétation de commandes en langage naturel
- Ajout de "!" aux commandes techniques


USAGE:
-----

Usage: sudo ./multisensor.py [-v|-d] &
	-v : Mode verbose (affiche sur la console les messages de log étendu)
	-d : Mode debug (n'envoie pas de SMS)

Arrêt: sudo ./stop_multisensor.py [-v]
	-v : Mode verbose (affiche sur la console les messages de log étendu)

Vérification si le programme est vivant (à mettre dans le CRON): sudo ./check_multisensor.py


PRÉREQUIS:
---------

Nécessite:
- un fichier de données de sensor dans ~/MonitoringSMS/multi_location_data.txt
	structure: tel_sensor [TAB] nom [EOF]
- un fichier de configuration dans /home/pi/MonitoringSMS/monitor_sms.conf contenant:
	send_email, pass_email [pour l'envoi d'email par gmail], 
	SMS_FREE [num du serveur SMS de FREE], 
	tel_admin [num du tel de l'administrateur], add_admin [adresse email de l'admin]

La carte NadHAT doit être éteinte au lancement du programme (?)


EFFETS DE BORD:
--------------

Créé dans ~/MonitoringSMS/ :
- un fichier log dans log_multisonde.log
- un fichier de liste des SMS reçus dans sms_in.log
- un fichier de liste des SMS envoyés dans sms_out.log
- in fichier de liste des erreurs dans log_err_multisonde.log
- un fichier CSV de données pour chaque sensor :[name_sensor]_data.txt
	structure: date [TAB] temp [TAB] humi [TAB] volt [CR]
- Un fichier png du dernier graphique des données pour chaque sensor : [name_sensor]_plot.png
- un fichier temporaire time_boot.txt de surveillance de boucles de reboot rapide

La carte NadHAt est arrêtée à la fin du programme (?)


FONCTIONNEMENT:
--------------

S'il reçoit un SMS d'une sonde contenant:
- "Armed", il extrait les données et les enregistre 
- "Lower", "Higher" ou "Normal", il extrait les données de l'alarme et les transmet à l'administrateur

S'il reçoit un SMS du numéro de l'administrateur débutant par:
- "Log", il envoie à l'email de l'administrateur le fichier de log 
- "LogIn" ou "Log In", il envoie à l'email de l'administrateur la liste des SMS reçus 
- "LogOut" ou "Log out", il envoie à l'email de l'administrateur la liste des SMS envoyés 
- "Log err", il envoie à l'email de l'administrateur le fichier de log des erreurs 
- "Sys", il renvoie en SMS les données de fonctionnement du raspberry
- "Ping [sensor]", il envoie une demande de données à la sonde ou à toutes les sondes
- "Data sensor adm", il envoie à l'email de l'administrateur un graphique et le tableau des données de la sonde 
- "Reboot", il reboote le système
- "Time" ou "Data", il renvoie un SMS avec la dernière date de collecte des données de toutes les sondes
- "Temp", il renvoie un SMS avec la dernière valeur de température de toutes les sondes
- "Humi", il renvoie un SMS avec la dernière valeur d'humidité de toutes les sondes
- "Volt", il renvoie un SMS avec la dernière valeur de voltage de toutes les sondes

S'il recoit un SMS d'un numéro quelconque débutant par:
- "Help" | "Aide" [sensor], il renvoie un SMS générique ou spécifique à la sonde d'aide sur les commandes
- "Time sensor", il renvoie un SMS avec la dernière date de collecte des données de la sonde
- "Temp sensor", il renvoie un SMS avec la dernière valeur de température de la sonde
- "Humi sensor", il renvoie un SMS avec la dernière valeur d'humidité de la sonde
- "Volt sensor", il renvoie un SMS avec la dernière valeur de voltage de la sonde
- "Data sensor", il renvoie un SMS avec la dernière date de collecte des données de la sonde
- "Data sensor [adresse@email]", il envoie à l'email adresse@email un graphique et le tableau des données de la sonde
- Sinon, il envoie le contenu du SMS à tel_admin

Par ailleurs, s'il reçoit un SMS débutant par:
- ["Lucie" | "Raphael"] valeur, envoie par socket un ordre de mise à jour de l'argent de poche
- "MWC" Num_tel PIN_conde, envoie par SMS le code PIN_code à Num_tel
- "Home", envoie par SMS le message "Je suis rentré à la maison" à l'admin

Sinon, si les données des sondes sont trop anciennes, envoie un SMS pour demander de nouvelles données
Sinon, s'il y a longtemps qu'il n'a pas envoyé de rappel des commandes, il les envoie pas SMS aux administrateur des sondes
Sinon, envoi un SMS de heartbeat à intervalle régulier avec les données système


REGLES D'ACTION:
---------------

Sur réception des données des sondes, des règles sont appliquées pour déclencher éventuellement l'envoi d'alertes 
vers l'administrateur des sondes et l'administrateur général

Pour toutes les sondes:
- Si le voltage est inférieur à limite_inf_volt
- Si la température est inférieure à limite_inf_temp

Pour la sonde "Tivine": (en cas de radiateur oublié)
- Si la température est supérieure à limite_sup_temp après 20h
- Si la température est supérieure à limite_sup_temp le week-end

Par ailleurs, les demandes de données ne sont pas envoyées vers "OuessantPi" (mode push uniquement)


PRINCIPE TECHNIQUE:
------------------

Boucle:
	Si break reçu, nettoyer et terminer
	Attendre un message SMS d'un émetteur
	Analyser le message
		S'il s'agit d'un message de sonde: 
			Mettre à jour données sonde de la table et les envoyer par socket
			Teste si les données demandent une alerte spécifique
		S'il est un élément du vocabulaire :
			Traiter le message suivant la grammaire
		S'il est inconnu, mal formé, ou l'émetteur n'a pas les droits nécessaires:
			Envoyer le message par SMS à l'administrateur
	Sinon si les données sont trop anciennes:
			Envoyer par SMS à chaque sonde une demande de données
	Sinon si l'envoi du rappel des commandes est trop ancien:
			Envoyer par SMS à chaque administrateur des sondes un rappel des commandes
	Sinon si le heartbeat est trop ancien:
			Envoyer par SMS à l'administrateur les dernières données système 


BUGS CONNUS:
-----------
Pas d'envoi de SMS accentués et décodage possible de SMS en réception uniquement avec é è à
-> Les noms des sondes et commandes ne peuvent pas inclure de ëêïîùû
-> Les messages d'alerte par SMS ne peuvent pas être accentués

"""

#-------------------------------------------------
#--- IMPORTS -------------------------------------
#-------------------------------------------------

import wiringpi
import serial
import time, sys
import datetime 
import os, signal
import csv
import ConfigParser
import smtplib
import re
#import unicodedata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import psutil
import socket
import Queue
import threading

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders


#-------------------------------------------------
#--- DEFINITIONS ---------------------------------
#-------------------------------------------------

# Port série et GPIO utilisés par NadHAT et codes d'erreur

serial_port = "/dev/ttyAMA0"
powerkey_GPIO = 26

code_NadHat={
	 0:"Successful request",
	 10:"Unsuccessful request",
	 11:"Unsuccessful assignement of the SMS server",
	 12:"Unsuccessful assignement of TEXT mode",
	 20:"No communication with NadHat",
	 30:"Unsuccessfull wake up of NadHat",
	 100:"No beginning found in message",
	 101:"No end found in message",
	 200:"Rank incorrect in message",
	 300:"Sender number incorrect in message",
	 301:"Sender number incorrect in message",
	 302:"Sender number incorrect in message",
	 }

code_NadHat_OK = 0
code_NadHat_NOK = 10
code_NadHat_NOK_server = 11
code_NadHat_NOK_text = 12
code_NadHat_nocom = 20
code_NadHat_nowake = 30

err_SMS_ok = 0
err_SMS_msg_start = 100
err_SMS_msg_end = 101
err_SMS_msg_rank = 200
err_SMS_num_start = 300
err_SMS_num_end = 301
err_SMS_num_digit = 302

# Numéros de téléphone et données pour l'envoi d'email (lus dans conf_filename)

SMS_server = ""			#	"+33695000695"
tel_admin= ""			#	"+33770044858"
addEmailFrom = ""		#	"kiting4free@gmail.com"
addEmailPass = ""		#	"kitenmnm"
addEmailAdm = ""		#	"mercouroff@gmail.com"

addEmailNPR = "ne-pas-repondre@gmail.com"

auth_adp = {'+33770044858':'Nicolas', '+33613052248':'Dominique'}
tel_server = "+33767274192"

# Chaines de caractère pré-définies

addEmailSubject = "Email Data "
panicEmailSubject = "PANIC RASPBERRY ZERO"
# msg_help1 = "AIDE SUR LES COMMANDES (1/2): Envoyez par SMS à ce numero '!Temp', '!Humi', ou '!Volt' suivi %s pour recevoir les dernières données collectées"
# msg_help2 = "AIDE SUR LES COMMANDES (2/2): Envoyez '!Data' suivi %s et d'une adresse email pour recevoir un graphique de la température et l'humidité"
msg_help = "AIDE SUR LES COMMANDES: Envoyez une requete en langage naturel pour recevoir par SMS ou par email les dernières données collectées pour %s"
msg_help_adm = "LISTE DES COMMANDES: '!Log' ['in'/'out'/err']/'!Sys'/'!Reboot', '!Ping'/'!Help' sonde, '!Data'/'!Time'/'!Temp'/'!Humi'/'!Volt' [sonde], '!Data' sonde 'adm'"

name_sensor_generique = "une sonde"
msg_erreur = "Desolé, cette commande est interdite. Pour la liste des commandes, envoyez 'Aide' suivi éventuellement du nom d'une sonde"
no_data_str = "Pas de données collectées pour le moment"
bold = '\033[1m'
warning = '\033[91m' # "\x1B[31;40m" # 
normal = '\033[00m'
underline = '\033[94m'

# Fichiers

path_filename = '/home/pi/MonitoringSMS/'
log_filename = 'log_multisonde.log'
log_err_filename = 'log_err_multisonde.log'
sms_in_filename = 'sms_in.log'
sms_out_filename = 'sms_out.log'
multi_location_filename = 'data_multisonde.txt'
conf_filename = 'conf_multisonde.conf'
bootdata_filename = 'time_multisonde.txt'
post_data_filename = '_data.txt'
post_plot_filename = '_plot.png'
CPU_temp = '/sys/class/thermal/thermal_zone0/temp'

# Structure des données dans multi_location_filename:
# (tel_sensor1 [TAB]	name_sensor1 [TAB]	num_admin [CR])+

# Structure des données dans chaque fichier name_sensor.txt:
# date_lieu [TAB] temp_lieu [TAB] humi_lieu [TAB] volt_lieu [CR]

data_type_list = {'!Time' : '', '!Temp':'C', '!Humi':'%', '!Volt':'V'}
children_list = {'Lucie', 'Raphael'}
dico_transl_command = {'Temperature':'!Temp','Heure':'!Time','Humidite':'!Humi','Voltage':'!Volt','Combien':'!Temp','Donnees':'!Data','Quand':'!Time','Aide':'!Help'}
command_resp = {"!Temp":"La température","!Humi":"L'humidité","!Volt":"Le voltage","!Time":"L'heure"}

dico_sensor_num = {}
dico_sensor_adm = {}
dico_num_sensor = {}

# Délai en s entre la vérification des SMS et de la sonde

delaiSMS = 5				# Période en secondes de la boucle principale
increment_query = 14400			# Récupérer data toutes les 4 heures
increment_heartbeat = 43200 # Envoyer un heartbeat toutes les 12 heures
increment_help = 604800 # Envoyer un rappel sur les aides toutes les semaines
min_delta_sec = 300			# Panic si reboot en moins de 5 minutes

# Nb de répétition de la procédure d'init et d'interrogation de la sonde avant exit

repet_init = 5

# Message de demande de données au RTU

msg_query_data = "1234EE"
msg_receive_data = "Armed"
msg_receive_alert_lo = "Lower"
msg_receive_alert_hi = "Higher"
msg_receive_normal = "Normal"

sms_out_count = 0
sms_in_count = 0
log_count = 0
err_count = 0

ip_receive = '192.168.31.167' #'eink-zero.local'
port_socket = 2718

#-------------------------------------------------
#--- PROCEDURES ----------------------------------
#-------------------------------------------------

#-------------------------------------------------
#		Gestion du log
#-------------------------------------------------

#---- Mode verbose ? (option "-v|-d")

def test_verbose(arg):

	if len(arg) < 2:
		return(False, False)

	if (arg[1] == "-v"):
		return(True, False)

	if (arg[1] == "-d"):
		return (True, True)


#---- Envoi des information vers le log

def tolog(txt):
	global log_count
	
	now = time.strftime('%Y/%m/%d %H:%M:%S')
	msg = "%s\t%s" % (now, txt)
	file = open(path_filename + log_filename, 'a')
	file.write(msg + "\n")
	file.close()
	log_count += 1
	return()

def tolog_info(text):
	if verbose:
		print("INFO\t" + text)
	tolog("INFO\t" + text)
	return()

def tolog_info_verb(text):
	if verbose:
		print("Info\t" + text)
		tolog("Info\t" + text)
	return()

def tolog_err(text):
	global err_count
	
	if verbose:
		print(warning + "ERR\t" + text + normal)

	now = time.strftime('%Y/%m/%d %H:%M:%S')
	msg = "%s\t%s" % (now, text)
	file = open(path_filename + log_err_filename, 'a')
	file.write(msg + "\n")
	file.close()
	err_count += 1

	tolog("ERR\t" + text)
	return()

def tolog_bold(text):
	if verbose:
		print(bold + time.strftime('%H:%M:%S') + "\t" + text + normal)
	tolog("INFO\t" + text)
	return()

def tolog_mark(text, msg):
	if verbose:
		print("INFO\t" + text + underline + msg + normal)
	tolog("INFO\t" + text + msg)
	return()


#---- Enregistrement des SMS reçus

def save_sms_in_log(msg, tel):
	global sms_in_count

	tolog_info_verb("Enregistrement du SMS entrant dans %s..." %(sms_in_filename))
	msg = msg.replace('\r', '') # Enlève les CR surnuméraires

	tolog_mark("SMS entrant venant de %s :\n" %(tel), msg)

	now = time.strftime('%Y/%m/%d %H:%M:%S')
	head = "==== SMS de %s le %s ====\n" % (tel, now)
	file = open(path_filename + sms_in_filename, 'a')
	file.write(head + msg + "\n")
	file.close()

	sms_in_count = sms_in_count + 1

	tolog_info_verb("...enregistrement OK !")

	return()


#---- Enregistrement des SMS envoyés

def save_sms_out_log(msg, tel):
	global sms_out_count

	tolog_info_verb("Enregistrement du SMS sortant dans %s..." %(sms_out_filename))
	tolog_mark("SMS sortant vers %s :\n" %(tel), msg)

	now = time.strftime('%Y/%m/%d %H:%M:%S')
	head = "==== SMS envoyé à %s le %s ====\n" % (tel, now)
	file = open(path_filename + sms_out_filename, 'a')
	file.write(head + msg + "\n")
	file.close()

	sms_out_count = sms_out_count + 1

	tolog_info_verb("...enregistrement OK !")

	return()


#-------------------------------------------------
#		Gestion sockets
#-------------------------------------------------

#---- Envoi des données via socket

def send_socket(msg):
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect((ip_receive, port_socket))
		sock.send(msg)
		time.sleep(3)	# Laisse 3 secondes au pi en réception…
		sock.close()	# …et ferme le socket
	except:
		return (False)

	return(True)


#---- Collection des données à envoyer via socket


def send_data_socket(name_sensor):

	tolog_info_verb('Envoi par socket des données de %s' %(name_sensor))

	data_time = last_data_sensors[name_sensor]['!Time']
	data_temp = last_data_sensors[name_sensor]['!Temp']
	data_humi = last_data_sensors[name_sensor]['!Humi']
	data_volt = last_data_sensors[name_sensor]['!Volt']

	text = "%s\t%s\t%s\t%s\t%s" %(name_sensor, data_time, data_temp, data_humi, data_volt)
	
	ok = send_socket(text)
	
	if ok:
		tolog_info_verb('...envoi des données OK')
	else:
		tolog_err("Erreur sur l'envoi par socket des données de %s" %(name_sensor))

	return (ok)


#---- Boucle d'envoi des données via socket

def loop_send_socket():
	global queue_data
	
	tolog_info_verb("Début du thread d'envoi de données par socket")

	while True:
		try:
			if not queue_data.empty():
				name_sensor = queue_data.get()
				if not (name_sensor in dico_sensor_num):
					tolog_err("Donnée pour une sonde inconnue à envoyer: %s" %(name_sensor))
					continue
				
				tolog_info_verb("Données à envoyer pour la sonde %s" %(name_sensor))
			
				if send_data_socket(name_sensor):
					tolog_info_verb("Données envoyées pour la sonde %s" %(name_sensor))
				else:
					tolog_info_verb("Données non envoyées pour la sonde %s" %(name_sensor))
		except:
			return()
	return()


#-------------------------------------------------
#		Gestion fichiers
#-------------------------------------------------

#---- Lecture des données de configuration 

def read_conf():

	full_conf_filename = path_filename + conf_filename

	tolog_info_verb("Lecture du fichier de configuration...")

	if not os.path.isfile(full_conf_filename):
		tolog_err("Le fichier de conf %s n'existe pas, désolé je ne peux rien faire !" % (conf_filename))
		tolog_bold("-------------- THE END ----------------")
		sys.exit(255)

	param = {}
	config = ConfigParser.ConfigParser()
	config.read(full_conf_filename)

	param['send_email'] = config.get('SMSAPI','send_email')
	param['pass_email'] = config.get('SMSAPI','pass_email')
	param['SMS_server'] = config.get('SMSAPI','SMS_FREE')
	param['tel_admin'] = config.get('SMSAPI','tel_admin')
	param['addEmailAdm'] = config.get('SMSAPI','email_admin')

	tolog_info_verb("...lecture du fichier de configuration OK")

	return (param)


#---- Lecture table des sondes

def read_multi_location():

	full_multi_location_filename = path_filename + multi_location_filename

	tolog_info_verb("Lecture du fichier des sondes...")

	if not os.path.isfile(full_multi_location_filename):
		tolog_err("Le fichier des sondes %s n'existe pas, désolé il n'y a rien à faire !" % (multi_location_filename))
		stop_nadhat()
		sys.exit(255)

	# Structure des données des sensors : (NumSonde [TAB] NomSonde [TAB] AdmSonde [CR])*

	location_file = open(full_multi_location_filename, 'r')
	i = 0
	while True:
		i = i+1
		data_line = location_file.readline()
		if data_line == '':
			tolog_info_verb('Les %s lignes de %s ont toutes été lues !' % (i, multi_location_filename))
			break

		split_list = data_line.split('\t')

		num_sensor = split_list[0]
		loc_sensor = normalize_str(split_list[1])
		adm_sensor = split_list[2]
		adm_sensor = adm_sensor.replace('\r', '')	# Enlève les CR surnuméraires
		adm_sensor = adm_sensor.replace('\n', '')	# Enlève les CR surnuméraires
		dico_num_sensor[num_sensor] = loc_sensor
		dico_sensor_num[loc_sensor] = num_sensor
		dico_sensor_adm[loc_sensor] = adm_sensor
#		tolog_info_verb("La ligne %s pour %s contient le numéro de sensor %s et le numéro d'admin %s" %(i, loc_sensor, num_sensor, adm_sensor))
		continue

	location_file.close()

	tolog_info_verb("...lecture du fichier %s OK" %(multi_location_filename))

	return()


#---- Ecriture table des données

def save_data_file(name_sensor):

	data_filename = name_sensor + post_data_filename
	full_data_filename = path_filename + data_filename

	tolog_info_verb('Ecriture du fichier des données de %s...' % (name_sensor))

	data_time = last_data_sensors[name_sensor]['!Time']
	data_temp = last_data_sensors[name_sensor]['!Temp']
	data_humi = last_data_sensors[name_sensor]['!Humi']
	data_volt = last_data_sensors[name_sensor]['!Volt']

	temp = float(data_temp)
	humi = float(data_humi)
	time = datetime.datetime.strptime(data_time, '%Y/%m/%d %H:%M:%S')
	data_list_temp_sensors[name_sensor].append(temp)
	data_list_humi_sensors[name_sensor].append(humi)
	data_list_date_sensors[name_sensor].append(time)

	data_file = open(full_data_filename, 'a')
	data_file.write("%s\t%s\t%s\t%s\n" %(data_time, data_temp, data_humi, data_volt))
	data_file.close()

	tolog_info_verb('...écriture du fichier %s OK' %(data_filename))

	return()


#---- Lecture table des données

def read_data(name_sensor):
	global data_list_temp_sensors, data_list_humi_sensors, data_list_date_sensors, last_data_sensors

	tolog_info_verb('Lecture du fichier des données de %s...' % (name_sensor))

	data_filename = name_sensor + post_data_filename
	full_data_filename = path_filename + data_filename

	last_data_sensors[name_sensor]['!Time'] = no_data_str
	last_data_sensors[name_sensor]['!Temp'] = no_data_str
	last_data_sensors[name_sensor]['!Humi'] = no_data_str
	last_data_sensors[name_sensor]['!Volt'] = no_data_str


	if not os.path.isfile(full_data_filename):
		tolog_info_verb('Pas de fichier des données pour %s...' % (name_sensor))
		return()

	data_file = open(full_data_filename, 'r')
	i = 0
	while True:
		i = i+1
		data_line = data_file.readline()
		if data_line == '':
			tolog_info_verb('Les %s lignes de %s ont toutes été lues !' % (i, data_filename))
			break

		split_data_line = data_line.split('\t')

#		try:
#			date = datetime.datetime.strptime(split_data_line[0], '%Y/%m/%d %H:%M:%S')
#			data_list_date_sensors[name_sensor].append(date)
#			temp = float(split_data_line[1])
#			data_list_temp_sensors[name_sensor].append(temp)
#			humi = float(split_data_line[2])
#			data_list_humi_sensors[name_sensor].append(humi)
#		except ValueError:
#			tolog_info_verb('La ligne %s ne contient pas de données numériques !' %(i))
#			continue
		date = datetime.datetime.strptime(split_data_line[0], '%Y/%m/%d %H:%M:%S')
		data_list_date_sensors[name_sensor].append(date)
		temp = float(split_data_line[1])
		data_list_temp_sensors[name_sensor].append(temp)
		humi = float(split_data_line[2])
		data_list_humi_sensors[name_sensor].append(humi)
		continue

	data_file.close()
	try:
		last_data_sensors[name_sensor]['!Time'] = split_data_line[0]
		last_data_sensors[name_sensor]['!Temp'] = split_data_line[1]
		last_data_sensors[name_sensor]['!Humi'] = split_data_line[2]
		last_data_sensors[name_sensor]['!Volt'] = split_data_line[3][:-1]
	except:
		tolog_info_verb('Pas de données numériques trouvées pour %s !' %(name_sensor))
		return()

	tolog_info_verb('...lecture du fichier %s OK' %(data_filename))

	return()


#---- Création du graphique des données de température & humidité

def plot_data(name_sensor):

	global data_list_temp_sensors, data_list_humi_sensors, data_list_date_sensors

	plot_temp_filename = name_sensor + post_plot_filename
	full_temp_filename = path_filename + plot_temp_filename

	tolog_info_verb('Ecriture du graphique des températures de %s...' % (name_sensor))

	date = data_list_date_sensors[name_sensor][0].strftime("%d/%m/%y")
	legende = "Temperature & humidite de %s depuis le %s" %(name_sensor, date)

	fig, ax1 = plt.subplots()
	ax1.plot(data_list_date_sensors[name_sensor], data_list_humi_sensors[name_sensor], label='Humidite', color = 'b')
#	ax1.plot(data_list_date_sensors[name_sensor], data_list_humi_sensors[name_sensor], color = 'b')

	ax1.set_ylabel('Humidite', color = 'b')
#	ax1.legend(loc=3)
	ax2 = ax1.twinx()
#	ax2.plot(data_list_date_sensors[name_sensor], data_list_temp_sensors[name_sensor], color = 'r')
	ax2.plot(data_list_date_sensors[name_sensor], data_list_temp_sensors[name_sensor], label='Temperature', color = 'r')
	ax2.set_ylabel('Temperature', color = 'r')
#	ax2.legend(loc=2)
#	ax2.legend(loc=0)

	for t in ax1.get_yticklabels():
		t.set_color('b')

	for t in ax2.get_yticklabels():
		t.set_color('r')


	ax1.fmt_data = mdates.DateFormatter('%Y/%m/%d %H:%M:%S ')
	fig.autofmt_xdate()
	plt.title(legende)
	plt.grid(b='on')
	plt.savefig(full_temp_filename)
	plt.clf()

	tolog_info_verb('...écriture du fichier %s OK' % (plot_temp_filename))

	return()


#-------------------------------------------------
#		Utilitaires
#-------------------------------------------------

#---- Utilitaire de lecture de l'adresse IP

def read_ip():
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.connect(("8.8.8.8", 80))
	ip_num = sock.getsockname()[0]
	sock.close()
	return(ip_num)


#---- Utilitaire de lecture de la température du CPU

def read_CPU_temp():
	temp_file = open(CPU_temp, "r")
	data = str(temp_file.read())
	temp_file.close()
	return (float(data)/1000)


#-------------------------------------------------
#		Gestion panic & erreurs
#-------------------------------------------------


#---- Enregistrement des données dans le fichier de gestion de panic

def save_panic(data):

	full_bootdata_filename = path_filename + bootdata_filename

	tolog_info_verb("Enregistrement des données panic %s..." %(data))

	bootdata_file = open(full_bootdata_filename, "w")
	bootdata_file.write(data)
	bootdata_file.close()

	tolog_info_verb("...enregistrement des données dans le fichier %s OK" %(bootdata_filename))

	return()


#---- Lecture des données dans le fichier de gestion de panic

def read_panic():

	full_bootdata_filename = path_filename + bootdata_filename

	tolog_info_verb("Lecture des données panic...")

	bootdata_file = open(full_bootdata_filename, "r")
	data = str(bootdata_file.read())
	bootdata_file.close()

	tolog_info_verb("...lecture des données dans le fichier %s OK" %(bootdata_filename))

	return(data)


#---- Test si le raspberry est dans une boucle de reboot (mode panic)

def test_panic(time_boot_process):

	full_bootdata_filename = path_filename + bootdata_filename

	tolog_info_verb("Test panic...")

	pid = os.getpid()

	data_boot_process = time_boot_process.strftime('%Y/%m/%d %H:%M:%S') + '\t' + str(pid)
	tolog_info("Data boot = %s" %(data_boot_process))

	if not os.path.isfile(full_bootdata_filename):
		save_panic(data_boot_process)
		tolog_info_verb("...test panic OK")
		return(True)

	data_boot_old = read_panic()

	split_data_boot_old = data_boot_old.split('\t')
	boot_time = datetime.datetime.strptime(split_data_boot_old[0], '%Y/%m/%d %H:%M:%S')
	delta_boot = time_boot_process - boot_time
	delta_sec = delta_boot.total_seconds()
	pid_str_old = split_data_boot_old[1]

	if psutil.pid_exists(int(pid_str_old)):
		tolog_err("STOP: Processus %s déjà en cours d'exécution !!" %(pid_str_old))
		return(False)

	# Le processus n'existe pas, il y a juste à tester si nous sommes dans une boucle de reboot

	save_panic(data_boot_process)

	if delta_sec < min_delta_sec:
		msg = "Reboot du Raspberry en %s s" %(delta_sec)
		send_email(addEmailAdm, panicEmailSubject, msg)
		tolog_err("...test panic NOK")
		tolog_info("-------------- THE END ----------------")
		return(False)

	tolog_info_verb("...test panic OK")

	return(True)


#---- Effacement du fichier de contrôle de panic

def delete_panic():

	full_bootdata_filename = path_filename + bootdata_filename

	tolog_info_verb("Effacement du fichier panic...")

	os.remove(full_bootdata_filename)

	tolog_info_verb("...fichier panic effacé")

	return()


#---- Envoi d'un message d'erreur par SMS

def notify_err(msg):
	tolog_err(msg)
	reply = send_sms(msg, tel_admin)
	return()


#-------------------------------------------------
#		Gestion NadHAT
#-------------------------------------------------

#---- Envoi d'une impulsion à la carte NadHAT; on: t=1s, off: t=2s

def pulse (t):

	tolog_info_verb("Envoi de l'ordre PULSE de %s s..." %(t))

	wiringpi.digitalWrite(powerkey_GPIO,1)
	time.sleep(t)
	wiringpi.digitalWrite(powerkey_GPIO,0)

	tolog_info_verb("...ordre PULSE envoyé")

	return()


#---- Envoi d'une command à la carte NadHAT et read le résultat

def send_cmd(cmd):

	nadhat.write(cmd + '\r')
	time.sleep(3)
	reply = nadhat.read(nadhat.inWaiting())

#	tolog_info_verb("Réponse à la command %s :\n---\n%s---" %(cmd, reply))

	if "ERROR" in reply:
		tolog_err("Erreur de la carte NadHAT sur la commande " + cmd)

	return(reply)


#---- Efface les SMS

def delete_read_sms():
	reply = send_cmd('AT+CMGDA="DEL READ"') # Supprime tout SMS déjà lu
	return()

def delete_all_sms():
	reply = send_cmd('AT+CMGDA="DEL ALL"') # Supprime tout SMS 
	return()

def delete_sent_sms():
	reply = send_cmd('AT+CMGDA="DEL SENT"') # Supprime tout SMS envoyé
	return()

def delete_one_sms(msg_rank):
	reply = send_cmd('AT+CMGD=' + msg_rank) # Supprime un SMS lu
#	tolog_info_verb("Réponse à la suppression du message numéro %s : %s" %(msg_rank, reply))
	return()

def read_all_sms():
	reply = send_cmd('AT+CMGL="ALL"')
	msg_received = ("READ" in reply)

	return(msg_received, reply)


##---- Initialisation de la carte

def init_nadhat():

	tolog_info_verb("Initialisation de la carte NadHAT...")

	wiringpi.wiringPiSetupGpio()
	wiringpi.pinMode(powerkey_GPIO,1)

	# Wake up NadHAT (if necessary)

	pulse(1)
	tolog_info("La carte NadHAT a reçu l'ordre de démarrage")

	# Try repeat_init times to wakeup NadHat board

	repeat = 0
	while True:

		time.sleep(5)
		reply = send_cmd("AT")

		if "OK" in reply:
			tolog_info_verb("La carte NadHAT se réveille...")
			break

		tolog_info_verb("La carte NadHAT ne se réveille pas...")
		repeat += 1
		if (repeat == repeat_init):
			return(code_NadHat_nowake)

	# Send the SMS server number

	repeat = 0
	while True:

		time.sleep(5)
		reply = send_cmd('AT+CSCA="%s"' %(SMS_server))

		if "OK" in reply:
			tolog_info_verb("La carte NadHAT accepte le serveur...")
			break

		tolog_info_verb("La carte NadHAT n'accepte pas le serveur...")
		repeat += 1
		if (repeat == repeat_init):
			return(code_NadHat_NOK_server)
		
	# Switch to text mode

	reply = send_cmd("AT+CMGF=1")
	if not "OK" in reply:
		return(code_NadHat_NOK_text)

#	rep = send_cmd('AT+CSCS=?')
#	tolog_info("Réponse à la command 'AT+CSCS=?' : " + rep)
# 
#	rep = send_cmd('AT+CSCS="8859-1"')
#	tolog_info("Réponse à l'ordre de passer en mode ISO 8859-1 : " + rep)

	# Effacer les SMS présents

#	delete_all_sms()

	return(code_NadHat_OK)



#---- Nettoyage et arrêt de la carte nadhat

def stop_nadhat():

	tolog_info_verb("Demande d'arrêt de la carte NadHAT...")

#	delete_all_sms() # Supprime tout
#	delete_read_sms() # Supprime tout SMS lu

	now = time.strftime('%Y/%m/%d à %H:%M:%S')

	reply = send_sms("Ordre de fin de monitoring recu le %s" %(now), tel_admin)
	send_sys()

	rep = send_cmd("AT+CPOWD=1")
	time.sleep(3)
	pulse(2)

	tolog_info_verb("...la carte NadHAT est arrêtée")

	delete_panic()
	tolog_bold("-------------- THE END ----------------")

	return()


#---- Envoi de message SMS

def send_sms(msg, tel_destinataire):
	global time_heartbeat

	tolog_bold("Envoi d'un SMS à %s..." %(tel_destinataire))
	save_sms_out_log(msg, tel_destinataire)

	if tel_destinataire == tel_admin:	# S'il s'agit d'un SMS envoyé à l'admin...
		time_heartbeat = time.time()	# ...l'horaire du dernier signe de vie mis à jour

	if (debug):
		tolog_bold("Mode debug: SMS non envoyé")
	else:
		msg2 = translate_accent(msg)
		reply = send_cmd('AT+CMGS="%s"' %(tel_destinataire))
		reply = send_cmd(msg2 + chr(26))
		if not "OK" in reply:
			return(code_NadHat_NOK)

#	delete_read_sms() # Supprime tout SMS déjà lu
	delete_sent_sms() # Supprime tout SMS envoyé

	tolog_info_verb("...SMS envoyé avec succès")

	return(code_NadHat_OK)


#---- Envoi par SMS des données du system

def send_sys():
#	time_boot_process = datetime.datetime.now()
#	now = datetime.datetime.now()


	delta_CPU = ddhhmmss(time.time() - psutil.boot_time())
#	delta_CPU = datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y/%m/%d %H:%M:%S")
	delta_process = ddhhmmss((datetime.datetime.now() - time_boot_process).total_seconds())
	log_size = str_K(os.path.getsize(path_filename + log_filename))
	err_pct = float(err_count) / log_count * 100
	msg = "CPU: Temp = {:2.0f} C, IP = {}, en marche depuis {}\nSMS: {} envoyés, {} recus en {}\nErr: {:2.1f} %" 
	reply = send_sms(msg.format(read_CPU_temp(), read_ip(), delta_CPU, sms_out_count, sms_in_count, delta_process, err_pct), tel_admin)

	return()


#---- Envoi par SMS des données de toutes les sondes

def send_all_data(type, tel):

	msg = "Dernières données pour %s :"	 %(type)
	for name_sensor in dico_sensor_num:
		try:
			msg = msg + "\n%s : %s %s" %(name_sensor, last_data_sensors[name_sensor][type], data_type_list[type])
		except:
			continue

	reply = send_sms(msg, tel)
	return()


#---- Envoi par SMS d'une aide pour tous les administrateurs de sonde

def send_help():
	for name_sensor in dico_sensor_num:
#		name_sensor2 = "de " + name_sensor
		reply = send_sms(msg_help %(name_sensor), dico_sensor_adm[name_sensor])
#		reply = send_sms(msg_help2 %(name_sensor2), dico_sensor_adm[name_sensor])
	return()


#---- Nettoyage et arrêt en cas de CTRL C

def signal_handler(signal, frame):

	tolog_bold("Sortie du programme par Ctrl+C!")
	stop_nadhat()
	sys.exit(0)


#-------------------------------------------------
#		Exécution des commands reçues par SMS
#-------------------------------------------------


#---- Action sur command "Armed"

def decode_cmd_armed(name_sensor, msg):
	global last_data_sensors, queue_data

	tolog_info("Détection de SMS d'envoi de données venant de %s" %(name_sensor))

	last_data_sensors[name_sensor] = extract_data(msg)
	save_data_file(name_sensor)
	
	queue_data.put(name_sensor) # Demande d'envoi des données de la sonde par socket
	
	analyse_data(name_sensor)

	return(1)


#---- Decode alerte

def decode_alert(msg):

	if "Volt" in msg:
		debut = msg.find("Volt")
		alert = "alimentation"
	elif "Temp" in msg:
		debut = msg.find("Temp")
		alert = "température"
	elif "Humi" in msg:
		debut = msg.find("Humi")
		alert = "humidité"
	alert = alert + " à " + msg[debut+5:debut+10] + " pour "

	return(alert)


#---- Action sur command "Lower"

def decode_cmd_lower(name_sensor, msg):

	tolog_info_verb("Alarme 'lower' reçue par SMS venant de %s" %(name_sensor))
	reply = send_sms("ALERTE " + decode_alert(msg) + name_sensor, tel_admin)
	return()


#---- Action sur command "Higher"

def decode_cmd_higher(name_sensor, msg):

	tolog_info_verb("Alarme 'higher' reçue par SMS venant de %s" %(name_sensor))
	reply = send_sms("ALERTE " + decode_alert(msg) + name_sensor, tel_admin)
	return()


#---- Action sur command "Normal"

def decode_cmd_normal(name_sensor, msg):

	tolog_info_verb("Alarme normal reçue par SMS venant de %s" %(name_sensor))
	reply = send_sms("Fin d'alerte " + decode_alert(msg) + name_sensor, tel_admin)
	return()


#---- Action sur command "MWC"

def cmd_mwc(tel_emetteur, nb_commands, command1, command2, command3):

	if (tel_emetteur != tel_server) and (tel_emetteur != tel_admin):	# Si la demande ne vient pas du serveur de SMS de Free ou de l'admin
		notify_err("Détection de commande MWC par un téléphone non valide : %s" %(tel_emetteur))
		return(False)
	
	if (command2 == 'Home'):
		tolog_info("MWC: Détection de demande d'envoi de message à Mum")
		now = time.strftime('%H:%M:%S')
		reply = send_sms("Maman, il est %s et je suis de retour à la maison !" %(now), tel_admin)
		return(True)
		
	if (nb_commands != 3) or not (check_tel(command2)):
		notify_err("Détection de demande d'envoi de PIN mal formée : %s %s %s" %(command1, command2, command3))
		return(False)
	
	tolog_info("Détection de demande d'envoi de PIN à %s" %(command2))
	reply = send_sms("PIN for your account: %s" %(command3), command2)
	return(True)


#---- Action sur command "Home"

def cmd_home(tel_emetteur, nb_commands, command1, command2, command3):

	if (tel_emetteur != tel_server) and (tel_emetteur != tel_admin):	# Si la demande ne vient pas du serveur de SMS de Free ou de l'admin
		notify_err("Détection de commande 'Home' par un téléphone non valide : %s" %(tel_emetteur))
		return(False)

	tolog_info("Détection de demande d'envoi de message à maman")
	now = time.strftime('%H:%M:%S')
	reply = send_sms("Maman, il est %s et je suis de retour à la maison !" %(now), tel_admin)
	return(True)


#---- Action sur command "Log"

def cmd_log(tel_emetteur, nb_commands, command1, command2, email_dest):

	if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
		notify_err("Détection de demande de log par un téléphone non valide : %s. Aide envoyée" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	log_to_send = log_filename
	if nb_commands == 2:
		if command2 == "In":
			log_to_send = sms_in_filename
		elif command2 == "Out":
			log_to_send = sms_out_filename
		elif command2 == "Err":
			log_to_send = log_err_filename
			
	tolog_info("Détection de demande d'envoi de %s par %s" %(log_to_send, tel_emetteur))

	send_log_email(log_to_send, addEmailAdm)
	reply = send_sms("Envoi de %s à %s" %(log_to_send, addEmailAdm), tel_admin)
	return(True)


def cmd_login(tel_emetteur, nb_commands, command1, command2, email_dest):

	if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
		notify_err("Détection de demande de log par un téléphone non valide : %s. Aide envoyée" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	tolog_info("Détection de demande d'envoi de %s par %s" %(sms_in_filename, tel_emetteur))

	send_log_email(sms_in_filename, addEmailAdm)
	reply = send_sms("Envoi de %s à %s" %(sms_in_filename, addEmailAdm), tel_admin)
	return(True)


def cmd_logout(tel_emetteur, nb_commands, command1, command2, email_dest):

	if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
		notify_err("Détection de demande de log par un téléphone non valide : %s. Aide envoyée" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	tolog_info("Détection de demande d'envoi de %s par %s" %(sms_out_filename, tel_emetteur))

	send_log_email(sms_out_filename, addEmailAdm)
	reply = send_sms("Envoi de %s à %s" %(sms_out_filename, addEmailAdm), tel_admin)
	return(True)


#---- Action sur command "Sys"

def cmd_sys(tel_emetteur, nb_commands, command1, command2, email_dest):

	tolog_info("Détection de demande d'envoi d'info système par %s" %(tel_emetteur))

	if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
		notify_err("Détection de demande d'info système par un téléphone non valide : %s. Aide envoyée" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	send_sys()
	return(True)


#---- Action sur command "Reboot"

def cmd_reboot(tel_emetteur, nb_commands, command1, command2, email_dest):

	tolog_info("Détection de demande de reboot système par %s" %(tel_emetteur))

	if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
		notify_err("Détection de demande de reboot système par un téléphone non valide : %s. Aide envoyée" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	stop_nadhat()
	os.system("sudo reboot")	# Boom
	return(True)


#---- Action sur command "Ping"

def cmd_ping(tel_emetteur, nb_commands, command1, command2, email_dest):

	tolog_info("Détection de demande de ping de la sonde %s par %s" %(command2, tel_emetteur))

	if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
		notify_err("Détection de demande de ping d'une sonde par un téléphone non valide : %s" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	if nb_commands == 1:
		request_data_sensors()
		reply = send_sms("Ping envoyé à toutes les sondes !", tel_admin)
	elif nb_commands == 2:
		if not (command2 in dico_sensor_num):
			notify_err("Détection de demande de ping pour une sonde inconnue %s" %(command2))
			return(0)
		request_data_sensor(command2)
		reply = send_sms("Ping envoyé à %s !" %(command2), tel_admin)

	return(True)


#---- Action sur command "Adp"

def cmd_adp(tel_emetteur, nb_commands, command1, command2, command3):

	tolog_info("Demande par %s de gestion d'argent de poche de %s : %s" %(translate_tel(tel_emetteur), command1, command2))

	if not tel_emetteur in auth_adp:	# Si la demande ne vient pas d'un numéro autorisé
		notify_err("Détection de demande de gestion d'argent de poche par un téléphone non valide : %s" %(tel_emetteur))
		reply = send_sms(msg_erreur, tel_emetteur)
		return(False)

	msg = "Adp\t%s\t%s\t%s" %(command1, command2, tel_emetteur)
	ok = send_socket(msg)
	
	if not ok:
		notify_err("Problème de socket lors de la mise à jour par %s de l'argent de poche de %s" %(translate_tel(tel_emetteur), command1))
		return(False)

	reply = send_sms("Argent de poche de %s mis à jour !" %(command1), tel_emetteur)
	if (tel_emetteur != tel_admin):
		reply = send_sms("Argent de poche de %s mis à jour par %s !" %(command1, translate_tel(tel_emetteur)), tel_admin)
	return (True)


#---- Action sur command "Data"

def cmd_data(tel_emetteur, nb_commands, command, name_sensor, email_dest):

	global data_list_temp_sensors, data_list_date_sensors

	if nb_commands == 1:	# S'il n'y a que "Data" dans le message
		tolog_info("Détection de demande par %s d'état pour toutes les sondes" %(tel_emetteur))

		if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
			notify_err("Détection de commande 'Data' par un téléphone non valide %s. Aide envoyée" %(tel_emetteur))
			reply = send_sms(msg_erreur, tel_emetteur)
			return(False)

		send_all_data('!Time', tel_emetteur)
		return(True)

	if not (name_sensor in dico_sensor_num):
		notify_err("Détection de demande de données pour une sonde inconnue %s" %(name_sensor))
		return(False)

	tolog_info("Détection de demande par %s d'état de %s" %(tel_emetteur, name_sensor))

	if nb_commands == 2:	# S'il n'y a que "Data Sonde" dans le message

		msg = "Etat de %s:" %(name_sensor)

		for clef in data_type_list:
			msg = msg + "\n%s = %s %s" %(clef, last_data_sensors[name_sensor][clef], data_type_list[clef])

		reply = send_sms(msg, tel_emetteur)
		return(True)

	if (email_dest.title() == "Adm") or (email_dest.title() == "Admin"):
		email_dest = addEmailAdm

	if not check_email(email_dest):
		return(False)
		
	msg = "Envoi des fichiers données et graphique de %s à %s" %(name_sensor, email_dest)
	plot_data(name_sensor)
	send_data_email(email_dest, name_sensor)
	reply = send_sms(msg, tel_emetteur)
	return(True)


#---- Action sur command "Help"

def cmd_help(tel_emetteur, nb_commands, command, command2, email_dest):
	global dico_sensor_adm

	if nb_commands == 1:	# S'il n'y a que "Help" dans le message
		tolog_info("Détection de demande par %s d'envoi d'une aide générale" %(tel_emetteur))
		
		if tel_emetteur == tel_admin:
			reply = send_sms(msg_help_adm, tel_admin)
			return(True)
		
		name_sensor2 = name_sensor_generique
		tel = tel_emetteur
		
	else:
		if check_tel(command2):
			tel = command2
			tolog_info("Détection de demande par %s d'envoi d'une aide pour le numero %s" %(tel_emetteur, command2))
			name_sensor2 = name_sensor_generique
			
		elif command2 in dico_sensor_num:
			tel = dico_sensor_adm[command2]
			tolog_info("Détection de demande par %s d'envoi d'une aide pour la sonde %s" %(tel_emetteur, command2))
			name_sensor2 = command2
			
		else:
			notify_err("Détection de demande pas %s d'aide pour une sonde inconnue %s" %(tel_emetteur, command2))
			return(False)

	reply = send_sms(msg_help %(name_sensor2), tel)
#	reply = send_sms(msg_help2 %(name_sensor2), tel)
	reply = send_sms("Aide envoyée à %s" %(tel), tel_admin)
	return(True)


#---- Action sur une commande du vocabulaire

def cmd_voc(tel_emetteur, nb_commands, command, name_sensor, email_dest):
	global last_data_sensors

	tolog_info_verb("Analyse de la command %s venant de %s pour la sonde %s..." %(command, tel_emetteur, name_sensor))

	if nb_commands == 1:		# S'il n'y a que "Commande" dans le message, renvoyer l'état de toutes les sensors
		tolog_info("Détection de demande par %s de %s pour toutes les sondes" %(tel_emetteur, command))

		if tel_emetteur != tel_admin:	# Si la demande ne vient pas de l'admin
			notify_err("Détection de commande '%s' par un téléphone non valide %s, aide envoyée" %(command, tel_emetteur))
			reply = send_sms(msg_erreur, tel_emetteur)
			return(False)

		send_all_data(command, tel_emetteur)
		return(True)

	if not (name_sensor in dico_sensor_num):
		notify_err("Détection de demande de %s pour une sonde inconnue %s" %(command, name_sensor))
		return(False)

	tolog_info("Détection de SMS de demande de %s pour %s" %(command, name_sensor))

	data_time = last_data_sensors[name_sensor]['!Time'].split()

	msg = "%s de la sonde %s le %s à %s est de %s %s" %(command_resp[command], name_sensor, data_time[0], data_time[1], last_data_sensors[name_sensor][command], data_type_list[command])
	reply = send_sms(msg, tel_emetteur)
	return(True)


#---- Action sur command inconnue

def alert_unknown_command(tel_emetteur, msg_sms, msg_rank):
	notify_err("Erreur lecture de SMS de rang %s venant de %s : >>>\n%s\n<<<" %(msg_rank, tel_emetteur, msg_sms))
	return(False)


#---- Extraction des commands du message

# def extract_command(msg_sms):
# 
# 	tolog_info_verb("Extraction des commandes d'un message...")
# 
# 	msg_sms = msg_sms.replace('	 ', ' ')	# Replace les double espace en simple espace
# 	
# 	command_sms = msg_sms.split(' ')
# 	nb_commands = len(command_sms)
# 
# 	try :
# 		command1 = normalize_str(command_sms[0])
# 	except:
# 		return(False, 0, '', '', '')
# 	
# 	try :
# 		command2 = normalize_str(command_sms[1])
# 	except:
# 		return(True, 1, command1, '', '')
# 	
# 	try :
# 		command3 = command_sms[2]
# 	except:
# 		return(True, 2, command1, command2, '')
# 		
# 	return(True, 3, command1, command2, command3)


def extract_command(str):

	tolog_info_verb("Extraction des commandes d'un message...")

	word_list = str.split()
	command_name = ''
	sensor_name = ''
	email_dest = ''
	
	for word in word_list:
		word = normalize_str(word)
		word = convert_command(word)
		if (command_name == '') and (word in dico_commands):
			command_name = word
		if (sensor_name == '') and (word in dico_sensor_num):
			sensor_name = word
		if (email_dest == '') and (check_email(word)):
			email_dest = word

	if (command_name == ''):
		return(False, 0, '', '', '')
	tolog_info_verb("...commande %s détectée" %(command_name))

	if (sensor_name == ''):
		return(True, 1, command_name, '', '')
	tolog_info_verb("...sonde %s détectée" %(sensor_name))
	
	if (email_dest == ''):
		return(True, 2, command_name, sensor_name, '')
	tolog_info_verb("...email %s détecté" %(email_dest))

	return(True, 3, command_name, sensor_name, email_dest)

#-------------------------------------------------
#		Extraction data SMS
#-------------------------------------------------

#---- Extraction du rang du SMS, du numéro de l'appelant et du message

def extract_sms(chaine):

	tolog_info_verb("Extraction d'informations d'un SMS...")

	# Recherche du premier SMS dans la liste

	debut = chaine.find('+CMGL:') # Rechercher le premier SMS
	if (debut == -1): # Si pas de marqueur trouvé, erreur de lecture
		tolog_err("Erreur d'interprétation des SMS: Pas de marqueur de début de SMS >>>\n%s" %(chaine))
		return(False, "","Erreur lecture debut SMS","")

	# Recherche du rang du premier SMS

	fin = chaine.find(',', debut) # Rechercher la fin de l'index du SMS
	if (fin == -1): # Si pas de marqueur trouvé, erreur de lecture
		tolog_err("Erreur d'interprétation des SMS: Pas de marqueur de fin d'index >>>\n%s" %(chaine))
		return(False, "","Erreur lecture rang SMS", "")
	rank = chaine[debut+7:fin]
	if not rank.isdigit(): # Si le rang n'est pas un nb, erreur de lecture
		tolog_err("Erreur d'interprétation des SMS: Rang non numérique >>>\n%s" %(chaine))
		return(False, "", "Erreur lecture rang SMS", rank)

	# Recherche du numéro de l'appelant du premier SMS

	debut = chaine.find('READ')
	if (debut == -1): # Si pas de marqueur trouvé, erreur de lecture
		tolog_err("Erreur d'interprétation des SMS: Pas de marqueur de début de numéro >>>\n%s" %(chaine))
		return(False, "Erreur lecture appelant SMS", "", rank)

	debut = debut + 7	# Passer les caractères 'READ","'
	fin = chaine.find('"', debut)
	
	numero = chaine[debut:fin]
	ok = check_tel(numero)
	if not ok:
		tolog_err("Erreur d'interprétation des SMS: num de tel non numérique >>>\n%s" %(chaine))
		return(False, numero, "Erreur interpretation appelant SMS", rank)

#	debut = chaine.find('+33')
#	if (debut == -1): # Si pas de marqueur trouvé, erreur de lecture
#		tolog_err("Erreur d'interprétation des SMS: Pas de marqueur de début de numéro >>>\n%s" %(chaine))
#		return(False, "","Erreur lecture appelant SMS","")
# 
#	fin = debut + 12
#	numero = chaine[debut:fin]
#	numero1 = chaine[debut+1:fin]
#	if not numero1.isdigit(): # Si le numéro n'est pas un nb, erreur de lecture
#		tolog_err("Erreur d'interprétation des SMS: num de tel non numérique >>>\n%s" %(chaine))
#		return(False, "", "Erreur lecture appelant SMS","")

	# Recherche du message du premier SMS

	debut = fin + 28
	fin = chaine.find('+CMGL:',debut) # Recherche le début du SMS suivant

	if fin == -1: # S'il n'y a pas de SMS suivant
		fin = chaine.rfind('OK') # Recherche le dernier OK
	if (fin == -1): # Si pas de marqueur trouvé, erreur de lecture
		tolog_err("Erreur d'interprétation des SMS: Pas de marqueur de fin de msg >>>\n%s" %(chaine))
		return(False, numero, "Erreur lecture payload SMS", rank)

	message = chaine[debut+1:fin-4]

	tolog_info("...SMS de rang %s reçu venant de %s" %(rank, numero))
	return (True, numero, message, rank)


#---- Extraction du message les données de la sonde 

def extract_data(msg):

	tolog_info_verb("Extraction de données d'un message...")

	data_sensor = {}

	# Lire le timestamp 

	data_sensor['!Time'] = time.strftime('%Y/%m/%d %H:%M:%S')

	# Lecture température

	debut = msg.find('Temp:')
	data_sensor['!Temp'] = msg[debut+5:debut+9]

	# Lecture humidité

	debut = msg.find('Humi:')
	data_sensor['!Humi'] = msg[debut+5:debut+7]

	# Lecture voltage

	debut = msg.find('Volt:')
	data_sensor['!Volt'] = msg[debut+5:debut+9]

	tolog_info_verb("...extraction de données OK")

	return(data_sensor)


#-------------------------------------------------
#		Utilitaires de strings	
#-------------------------------------------------

#---- Validation de l'adresse email, du nom de sonde, de la commande d'un message

def check_email(email):
	valid = re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email)
	return (valid)


def convert_command(str):
	if str in dico_transl_command:
		return(dico_transl_command[str])
	return(str)
	
# 	for name_cmd in dico_transl_command:
# 		if name_cmd == str:
# 			return (dico_transl_command[name_cmd])
# 	return ('')


#---- Validation du numéro de téléphone d'un message

def check_tel(numero):

	if numero.isdigit():
		return(True)

	# Si le numéro n'est pas un nb, essayer de retirer le "+" au début

	if numero[0] != '+':
		return(False)
		
	# Si le numéro n'est pas non plus un nb, erreur de lecture
	
	return (numero[1:].isdigit()) 


#---- Remplace le numéro de téléphone par le nom de la sonde

def translate_tel(tel):

	translated = tel
	
	try:
		translated = dico_num_sensor[tel]
	except:
		try:
			translated = auth_adp[tel]
		except:
			return(tel)
	
	return(translated)

#---- Replace les accents

def remove_accent(s):
	s2 = ''
	for ch in s:
		if hex(ord(ch)) == '0xe9':
			s2 = s2 + 'e'
		elif hex(ord(ch)) == '0xe8':
			s2 = s2 + 'e'
		elif hex(ord(ch)) == '0xe0':
			s2 = s2 + 'a'
		elif hex(ord(ch)) == '0xf9':
			s2 = s2 + 'u'
		else:
			s2 = s2 + ch
	return(s2)


def translate_accent(s):
	s = re.sub('é', '\xe9', s)
	s = re.sub('è', '\xe8', s)
	s = re.sub('à', '\xe0', s)
	s = re.sub('ù', '\xf9', s)
	s = re.sub('ç', 'c', s)
	s = re.sub('ê', 'e', s)
	s = re.sub('û', 'u', s)
	return(s)


def normalize_str(text):
#	tolog_info_verb("Normalisation de %s..." %(text))
	text = remove_accent(text)
# 	text = re.sub('éèêë','e', text)
# 	text = re.sub('à','a', text)
# 	text = re.sub('ù','u', text)
# 	text = re.sub('ç','c', text)
	text = text.title()
#	tolog_info_verb("...résultat: %s" %(text))

	return str(text)


def normalize_msg(str):

# 	str = str.replace('.', ' ')	# Replace les . en espace
# 	str = str.replace(',', ' ')	# Replace les , en espace
# 	str = str.replace('?', ' ')	# Replace les ? en espace
# 	str = str.replace('!', ' ')	# Replace les ! en espace
# 	str = str.replace('  ', ' ')	# Replace les double espace en simple espace

	words = str.split()
	str2 = ''
	for word in words:
		str2 += normalize_str(word) + ' '
	return (str2)


def str_K(n):	# Formate en séparant les milliers
	result = ''
	while n >= 1000:
		n, r = divmod (n, 1000)
		result = " %03d%s" % (r, result)
	return "%d%s" %(n, result)


def ddhhmmss(seconds):	# Formate en Heure:Minute:Seconde

	hour, seconds = divmod(seconds, 3600)
	min, seconds = divmod(seconds, 60)
	dhms = '%02.0fh%02.0fm%02.0fs' %(hour, min, seconds)
	return dhms


#-------------------------------------------------
#		Envoi d'email  
#-------------------------------------------------


#---- Envoi du log par email 

def send_log_email(filename, email):

	tolog_info("Envoi du fichier %s par email à %s..." %(filename, email))

	sujet = "Fichier log %s" %(filename)

	data_attachment = open(path_filename + filename, 'r')

	msgMail = MIMEMultipart()
	msgMail['Subject'] = sujet
	msgMail['From'] = addEmailFrom
	msgMail['To'] = email

	now = time.strftime('%Y/%m/%d %H:%M:%S')

	msg = MIMEText("Fichier %s généré le %s.\n\nWith love,\n\n-Raspberry.\n\n" %(filename, now), 'plain', 'utf-8')

	msgMail.attach(msg)

	part = MIMEBase('application', 'octet-stream')

	part.set_payload((data_attachment).read())
	encoders.encode_base64(part)
	part.add_header('Content-Disposition', "attachment; filename= %s" %(filename))
	msgMail.attach(part)

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(addEmailFrom, addEmailPass)
	body = msgMail.as_string()
	server.sendmail(addEmailFrom, email, body)
	server.quit()

	data_attachment.close()

	tolog_info_verb("...envoi du fichier %s par email OK" %(filename))

	return()


#---- Envoi d'email avec les fichiers de données

def send_data_email(email, name_sensor):

	tolog_info("Envoi des fichiers data de %s par email à %s..." %(name_sensor, email))

	sujet = addEmailSubject + name_sensor
	data_filename = name_sensor + post_data_filename
	full_data_filename = path_filename + data_filename
	plot_temp_filename = name_sensor +	post_plot_filename
	full_temp_filename = path_filename + plot_temp_filename

	data_attachment = open(full_data_filename, 'r')
	plot_attachment = open(full_temp_filename, 'rb')

	msgMail = MIMEMultipart()
	msgMail['Subject'] = sujet
	msgMail['From'] = addEmailFrom
	msgMail['To'] = email
	msgMail.add_header('reply-to', addEmailAdm) # addEmailNPR

#	now = time.strftime('%Y/%m/%d %H:%M:%S')
	now = last_data_sensors[name_sensor]['!Time']
	text = MIMEText("Données et graphique pour la sonde %s, en date du %s.\n\nWith love,\n\n-Raspberry.\n\n" %(name_sensor, now), 'plain', 'utf-8')
	msgMail.attach(text)

	part = MIMEBase('application', 'octet-stream')

	tolog_info_verb("Attachement du fichier " + plot_temp_filename)

	part.set_payload((plot_attachment).read())
	encoders.encode_base64(part)
	part.add_header('Content-Disposition', "attachment; filename= %s" %(plot_temp_filename))
	msgMail.attach(part)

	part = MIMEBase('application', 'octet-stream')

	tolog_info_verb("Attachement du fichier " + data_filename)

	part.set_payload((data_attachment).read())
	encoders.encode_base64(part)
	part.add_header('Content-Disposition', "attachment; filename= %s" %(data_filename))
	msgMail.attach(part)

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.ehlo()
	server.login(addEmailFrom, addEmailPass)
	body = msgMail.as_string()
	server.sendmail(addEmailFrom, email, body)
	server.quit()

	data_attachment.close()
	plot_attachment.close()

	tolog_info_verb("...envoi des fichiers %s & %s par email OK" %(data_filename, plot_temp_filename))

	return()


#---- Envoi d'email général

def send_email(email, sujet, msg):

	tolog_info("Envoi du mail '%s' à %s..." %(sujet, email))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()

	msgMail = MIMEMultipart()
	msgMail['From'] = addEmailFrom
	msgMail['To'] = email
	msgMail['Subject'] = sujet
	msgMail.add_header('reply-to', addEmailAdm) # addEmailNPR
	msgMail.attach(MIMEText(msg, 'plain', 'utf-8'))
	body = msgMail.as_string()

	server.login(addEmailFrom, addEmailPass)
	server.sendmail(addEmailFrom, email, body)
	server.quit()

	tolog_info_verb("...envoi de l'email OK")

	return()


#-------------------------------------------------
#		Demande et analyse les données des sensors	
#-------------------------------------------------

#--- Analyse des données

limite_sup_temp = 30
limite_inf_temp = 6
limite_inf_volt = 6
limite_heure_travail = 20 

def analyse_data(name_sensor):
	global last_data_sensors

	tolog_info_verb("Analyse des données reçues pour %s..." %(name_sensor))

	date_time = datetime.datetime.strptime(last_data_sensors[name_sensor]['!Time'], '%Y/%m/%d %H:%M:%S')
	num_heure = date_time.hour
	num_joursem = date_time.weekday()
	tel_admin_sensor = dico_sensor_adm[name_sensor]

	num_temp = float(last_data_sensors[name_sensor]['!Temp'])
	num_humi = float(last_data_sensors[name_sensor]['!Humi'])
	num_volt = float(last_data_sensors[name_sensor]['!Volt'])

	tolog_info_verb("Heure = %s, Jour = %s, Temp = %4.1f, Humi = %2.0f %%, Volt = %2.0f V" %(num_heure, num_joursem, num_temp, num_humi, num_volt))

	if num_volt < limite_inf_volt:
		tolog_bold("ALERTE disjoncteur à %s !" %(name_sensor))
		reply = send_sms("ALERTE: Plus d'alimentation à %s !" %(name_sensor), tel_admin)
		if tel_admin != tel_admin_sensor:
			reply = send_sms("ALERTE: Plus d'alimentation à %s !" %(name_sensor), tel_admin_sensor)
		return()

	if num_temp <= limite_inf_temp:
		tolog_bold("ALERTE risque de gel à %s !" %(name_sensor))
		reply = send_sms("ALERTE GEL: Température de %s de %sC, inferieure a %sC !" %(name_sensor, num_temp, limite_inf_temp), tel_admin)
		if tel_admin != tel_admin_sensor:
			reply = send_sms("ALERTE GEL: Température de %s de %sC, inferieure a %sC !" %(name_sensor, num_temp, limite_inf_temp), tel_admin_sensor)
		return()

	if name_sensor == "Tivine":
		if num_temp > limite_sup_temp:

			if (num_heure >= limite_heure_travail):
				tolog_bold("ALERTE oubli du radiateur à %s !" %(name_sensor))
				reply = send_sms("ALERTE OUBLI: Température de %s de %sC, superieure a %sC apres %sh !" %(name_sensor, num_temp, limite_sup_temp, limite_heure_travail), tel_admin)
				if tel_admin != tel_admin_sensor:
					reply = send_sms("ALERTE OUBLI: Température de %s de %sC, superieure a %sC apres %sh !" %(name_sensor, num_temp, limite_sup_temp, limite_heure_travail), tel_admin)
				return()

			if (num_joursem == 5) or (num_joursem == 6):
				tolog_bold("ALERTE oubli du radiateur à %s !" %(name_sensor))
				reply = send_sms("ALERTE OUBLI: Température de %s de %sC, superieure a %sC le weekend !" %(name_sensor, num_temp, limite_sup_temp), tel_admin)
				if tel_admin != tel_admin_sensor:
					reply = send_sms("ALERTE OUBLI: Température de %s de %sC, superieure a %sC le weekend !" %(name_sensor, num_temp, limite_sup_temp), tel_admin_sensor)
				return()

	tolog_info_verb("Données de %s OK" %(name_sensor))

	return()


#--- Requête des données

def request_data_sensor (name_sensor):
	if (name_sensor == "Ouessantpi"):
		tolog_info("Pas d'envoi de demande de données pour %s" %(name_sensor))
	else:
		tolog_info("Envoi d'une demande de data pour %s" %(name_sensor))
		reply = send_sms(msg_query_data, dico_sensor_num[name_sensor])
	return()

def request_data_sensors ():
	for name_sensor in dico_sensor_num:
		request_data_sensor(name_sensor)
	return()


#--- vérification de l'age des données

def check_time_sensors():
	OK = True
	alert_msg = ""
	now = datetime.datetime.now()
	for name_sensor in dico_sensor_num:
		time_sensor = data_list_date_sensors[name_sensor][-1]
		delta = (now - time_sensor).total_seconds()
#		tolog_info_verb("Delta pour la sonde %s : %s" %(name_sensor, delta))
		if (delta > 2 * increment_query):
			OK = False
			alert_msg = alert_msg + "\n%s depuis le %s" %(name_sensor, time_sensor)
	return (OK, alert_msg)


#-------------------------------------------------
#--- DEBUT DU PROGRAMME --------------------------
#-------------------------------------------------

dico_commands = {'Home':cmd_home,'Lucie':cmd_adp,'Raphael':cmd_adp,'!Ping':cmd_ping,'!Sys':cmd_sys,'!Reboot':cmd_reboot,'!Log':cmd_log,'!Login':cmd_login,'!Logout':cmd_logout,'!Data':cmd_data,'!Help':cmd_help,'!Time':cmd_voc,'!Temp':cmd_voc,'!Humi':cmd_voc,'!Volt':cmd_voc}
messages_sensor = {'Armed':decode_cmd_armed,'Lower':decode_cmd_lower,'Higher':decode_cmd_higher,'Normal':decode_cmd_normal}

if __name__ == "__main__":

	time_boot_process = datetime.datetime.now()

	(verbose, debug) = test_verbose(sys.argv)

	if (verbose):
		print("")
		
	tolog_bold("------------ BEGINNING ----------------")
	if (debug):
		tolog_info_verb("Mode debug = True")
	elif (verbose):
		tolog_info_verb("Mode verbose = True")
	else:
		tolog_info("Mode verbose = False")


#-------------------------------------------------
#		Chargement des données de configuration 
#-------------------------------------------------

	param = read_conf()

	addEmailFrom = param['send_email']
	addEmailPass = param['pass_email']
	SMS_server = param['SMS_server']
	tel_admin = param['tel_admin']
	addEmailAdm = param['addEmailAdm']


#-------------------------------------------------
#		Vérification si nous sommes dans une boucle de reboot
#-------------------------------------------------

	if not test_panic(time_boot_process):
		sys.exit(255)


#-------------------------------------------------
#		Initialisation de la carte
#-------------------------------------------------

	# Initialisation du port série

	nadhat = serial.Serial(
		port = serial_port,
		baudrate = 9600,
		parity = serial.PARITY_NONE,
		stopbits = serial.STOPBITS_ONE,
		bytesize = serial.EIGHTBITS,
		timeout = 3
	)

	code_err = init_nadhat()
	if not (code_err == code_NadHat_OK):
		tolog_err("Impossible d'initialiser nadhat: " + code_NadHat[code_err])
		delete_panic()
		tolog_info("-------------- THE END ----------------")
		sys.exit(1)
	tolog_info_verb("...la carte NadHAT fonctionne")

	sms_out_count = 0
	sms_in_count = 0

	now = time.strftime('%Y/%m/%d à %H:%M:%S')

	reply = send_sms("Debut de monitoring le %s" %(now), tel_admin)


#-------------------------------------------------
#		Lecture des données d'identifiant des multi sensors et initialisation
#-------------------------------------------------

	# Lecture des données sur le disque sous la forme d'un double dictionnaire

	read_multi_location()

	# Initialisation de la liste des données relevées pour chaque sensor

	data_list_temp_sensors = {}
	data_list_humi_sensors = {}
	data_list_date_sensors = {}
	last_data_sensors = {}
#	last_time_sensors = {}

	for name_sensor in dico_sensor_num:
		last_data_sensors[name_sensor] = {}
		data_list_temp_sensors[name_sensor] = []
		data_list_humi_sensors[name_sensor] = []
		data_list_date_sensors[name_sensor] = []
#		last_time_sensors[name_sensor] = 0
		read_data(name_sensor)

	time_sensor = 0
	time_heartbeat = 0
	time_help = time.time()


#-------------------------------------------------
#		Lancement de la boucle de gestion des sockets
#-------------------------------------------------

	queue_data = Queue.Queue()
	thread_soc = threading.Thread(target=loop_send_socket)
	thread_soc.daemon = True
	thread_soc.start()


#-------------------------------------------------
#		Boucle d'attente des SMS
#-------------------------------------------------

	while True:			# Boucle d'attente d'un SMS

		time.sleep(delaiSMS)	# Attendre le prochain SMS

		signal.signal(signal.SIGINT, signal_handler)	# Sortie du programme ?

		msg_received, reply = read_all_sms()	# Lire les SMS dans la mémoire

		if msg_received:		# Si un SMS a été reçu, read le SMS

			tolog_bold("SMS reçu !")

			(ok, tel_emetteur, msg_sms, msg_rank) = extract_sms(reply)	# Extraire les données du SMS

			if msg_rank.isdigit():	# Si le message était bien dans la file d'attente
				tolog_info_verb("Effacement du message %s de la file d'attente" %(msg_rank))
				delete_one_sms(msg_rank)	# Effacer le SMS lu

			if not ok:	# S'il y a eu un problème lors de la récupérations des données du SMS
				alert_unknown_command(tel_emetteur, msg_sms, msg_rank)
				continue

			tolog_info_verb("Enregistrement du message %s" %(msg_rank))
			save_sms_in_log(msg_sms, tel_emetteur)	# Enregistre le SMS reçu

			#	Décodage du message

			if tel_emetteur in dico_num_sensor:
			
				sensor_name = dico_num_sensor[tel_emetteur]
								
				if msg_receive_data in msg_sms:		# Si le SMS contient Armed
					decode_cmd_armed(sensor_name, msg_sms) # Extraire les données et les enregistrer
					continue
			
				if msg_receive_alert_lo in msg_sms:		#Si le SMS contient Lower
					decode_cmd_lower(sensor_name, msg_sms)
					continue
			
				if msg_receive_alert_hi in msg_sms:		#Si le SMS contient Higher
					decode_cmd_higher(sensor_name, msg_sms)
					continue
			
				if msg_receive_normal in msg_sms:		#Si le SMS contient normal
					decode_cmd_normal(sensor_name, msg_sms)
					continue
			
				# Traitement spécial pour les messages venant de la box
				if "Home" in msg_sms:
					cmd_home(tel_emetteur, 1, 'Home', '', '')
					continue
				
				msg_sms = "Message inconnu recu de %s : '%s'" %(sensor_name, msg_sms)
				alert_unknown_command(tel_emetteur, msg_sms, msg_rank)

			(ok, nb_commands, command1, command2, command3) = extract_command(msg_sms)	# Sinon, décoder la commande

			if not ok:					# Si la commande est mal formée
				notify_err("SMS incorrect venant de %s : '%s'" %(translate_tel(tel_emetteur), msg_sms))
				continue

			if command1 in dico_commands:	# S'il s'agit d'une commande, l'analyser
				ok = dico_commands[command1](tel_emetteur, nb_commands, command1, command2, command3)
				if not ok:
					notify_err("Erreur d'exécution de la commande '%s' venant de %s" %(command1, translate_tel(tel_emetteur)))
				continue

			alert_unknown_command(tel_emetteur, msg_sms, msg_rank)	# Sinon, renvoyer tel quel le message inconnu à l'administrateur

			continue

#	Sinon, si aucun SMS à traiter...


#	...vérifier si les données des sensors sont à jour

		if time.time() - time_sensor >= increment_query:	# S'il est temps de vérifier les données
			tolog_info("Vérification et rafraichissement des données sondes")

			(OK, alert_msg) = check_time_sensors()
		
			if not OK:	# Si les données sont trop anciennes
				tolog_info("Données de sonde manquantes")
				reply = send_sms("ALERTE données sondes manquantes:" + alert_msg, tel_admin)

			tolog_info("Rafraichissement des données des sondes")
			time_sensor = time.time()
			request_data_sensors()	# Demander les dernières données des sensors
			
			continue


#	...vérifier si un rappel des commandes doit être envoyé

		if time.time() - time_help >= increment_help:	# S'il est temps d'envoyer un heartbeat
			tolog_info("Envoi de message d'aide")
			send_help()
			time_help = time.time()

			continue

#	...vérifier si un hearbeat doit être envoyé

		if time.time() - time_heartbeat >= increment_heartbeat: # S'il est temps d'envoyer un heartbeat
			tolog_info("Envoi d'un heartbeat")
			send_sys()
#			send_all_data('!Time', tel_admin)	# Envoyer dates des dernières récupérations de données de sensors
#			time_heartbeat = time.time()


		continue


#-------------------------------------------------
#----- FIN DU PROGRAMME --------------------------
#-------------------------------------------------
