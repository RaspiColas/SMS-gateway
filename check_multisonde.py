#!/usr/bin/python
# -*- coding: utf-8 -*-

#---------------------------------------------------#
#													#
#				check_multisonde.py					#
#													#
#---------------------------------------------------#

"""
Version: 19/4/18

Programme Python destiné à vérifier l'état du programme "multisonde.py", gestionnaire de capteurs RTU5023 


HISTORIQUE:
-----------
19/4/18:
- Changement de l'ordre de reboot en '!Restart'
- Ajout de mécanisme de découpe de tous les log

"""

import wiringpi
import serial
import time, sys
import datetime 
import os, signal
#import csv
import ConfigParser
import smtplib
#import re
import psutil

from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders


#-------------------------------------------------
#--- DEFINITIONS ---------------------------------
#-------------------------------------------------

# Port série et GPIO utilisés par NadHAT

PORT_SERIE = "/dev/ttyAMA0"
POWER_KEY_GPIO = 26

# Numéros de téléphone et données pour l'envoi d'email (lus dans conf_filename)

SMS_server = ""			#	"+33695000695"
tel_admin= ""			#	"+33770044858"
addEmailFrom = ""		#	"kiting4free@gmail.com"
addEmailPass = ""		#	"kitenmnm"
addEmailAdm = ""		#	"mercouroff@gmail.com"


# Chaines de caractère pré-définies

addEmailSubject = "Email Data "
panicEmailSubject = "MONITEUR SONDES ARRETE"
bold = '\033[1m'
warning = '\033[91m' # "\x1B[31;40m" # 
normal = '\033[00m'
underline = '\033[94m'
msg_alert = "Moniteur de sonde arrete !"
msg_restart = "\nRestart ?"
msg_reboot = "Reboot du systeme !"

# Fichiers

path_filename = '/home/pi/MonitoringSMS/'
pre_log_filename = 'log_multisonde'
pre_sms_in_filename = 'sms_in'
pre_sms_out_filename = 'sms_out'
post_log_filename = '.log'
conf_filename = 'conf_multisonde.conf'
bootdata_filename = 'time_multisonde.txt'
nom_commande = 'multisonde.py'



limit_log_size = 200000
delay_reply = 60 	# Temps d'attente de réponse de restart

#-------------------------------------------------
#--- PROCEDURES ----------------------------------
#-------------------------------------------------

#-------------------------------------------------
# 		Gestion du log
#-------------------------------------------------


#---- Mode verbose ? (option "-v")

def test_verbose(arg):

	if len(arg) < 2:
		return(False, False)

	if (arg[1] == "-v"):
		return(True, False)
	
	if (arg[1] == "-d"):
		return (True, True)


#---- Envoi des information vers le log

def tolog(txt):
	now = time.strftime('%Y/%m/%d %H:%M:%S')
	msg = "%s\t%s" % (now, txt)
	file = open(path_filename + pre_log_filename + post_log_filename, 'a')
	file.write(msg + "\n")
	file.close()
	return()

def tolog_info(text):
	if verbose:
		print("INFO\tCRON: " + text)
	tolog("INFO\tCRON: " + text)
	return()

def tolog_info_verb(text):
	if verbose:
		print("Info\tCRON: " + text)
		tolog("Info\tCRON: " + text)
	return()

def tolog_err(text):
	if verbose:
		print(warning + "ERR\tCRON: " + text + normal)
	tolog("ERR\tCRON: " + text)
	return()

def tolog_bold(text):
	if verbose:
		print(bold + time.strftime('%H:%M:%S') + "\tCRON: " + text + normal)
	tolog("INFO\tCRON: " + text)
	return()


#---- Vérification de la taille du log

def check_log_size(file_name):
	now = time.strftime('-%y%m%d')
	log_filename_full = path_filename + file_name + post_log_filename
	size = os.path.getsize(log_filename_full)
	if size > limit_log_size:
		os.rename(log_filename_full, path_filename + file_name + now + post_log_filename)
	return()


def check_log():
	check_log_size(pre_log_filename)
	check_log_size(pre_sms_in_filename)
	check_log_size(pre_sms_out_filename)
	return()
	

#-------------------------------------------------
# 		Gestion fichiers
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


#---- Extraction de l'identifiant de la tache à partir du fichier

def get_pid_str():

	full_bootdata_filename = path_filename + bootdata_filename
	
	if not os.path.isfile(full_bootdata_filename):
		return('')

	bootdata_file = open(full_bootdata_filename, "r")
	data_boot = str(bootdata_file.read())
	bootdata_file.close()
	
	split_data_boot = data_boot.split('\t')
	
	if len(split_data_boot) == 2:
		return (split_data_boot[1])

	return ('')


#---- Effacement du fichier de contrôle de panic

def efface_panic():

	full_bootdata_filename = path_filename + bootdata_filename

	tolog_info_verb("Effacement du fichier panic...")

	if os.path.isfile(full_bootdata_filename):
		os.remove(full_bootdata_filename)

	tolog_info_verb("...fichier panic effacé")

	return()


#-------------------------------------------------
# 		Gestion NadHAT et SMS
#-------------------------------------------------

#---- Envoi d'une impulsion à la carte NadHAT; on: t=1s, off: t=2s

def pulse (t):

	tolog_info_verb("Envoi de l'ordre PULSE de %s s..." %(t))

	wiringpi.digitalWrite(POWER_KEY_GPIO,1)
	time.sleep(t)
	wiringpi.digitalWrite(POWER_KEY_GPIO,0)

	tolog_info_verb("...ordre PULSE envoyé")

	return()


#---- Envoi d'une commande à la carte NadHAT et lire le résultat

def send_cmd(cmd):

	nadhat.write(cmd + '\r')
	time.sleep(3)
	reply = nadhat.read(nadhat.inWaiting())

#	tolog_info_verb("Réponse à la commande %s :\n---\n%s---" %(cmd, reply))

	if "ERROR" in reply:
		tolog_err("Erreur de la carte NadHAT sur la commande " + cmd)

	return(reply)


#---- Initialisation de la carte

def init_nadhat():

	tolog_info_verb("Initialisation de la carte NadHAT...")

	# Utiliser la numerotation GPIO et mettre le GPIO en mode sortie = 1

	wiringpi.wiringPiSetupGpio()
	wiringpi.pinMode(POWER_KEY_GPIO,1)

	# Réveiller le NadHAT (si nécessaire)

	pulse(1)
	tolog_info("La carte NadHAT a reçu l'ordre de démarrage")

	# Vérifier repet_init fois la communication avec la carte NadHAT jusqu'à ce qu'elle se réveille

	repet = 0
	while True:

		time.sleep(5)
		rep = send_cmd("AT")

		if rep == "":
			tolog_err("Exit: Pas de communication avec la carte NadHAT")
			tolog_info("-------------- THE END ----------------")
			sys.exit(1)

		if "OK" in rep:
			break

		else :
			tolog_err("La carte NadHAT ne répond pas OK")
			repet += 1
			if (repet == repet_init):
				tolog_err("Exit: la carte NadHAT ne répond pas OK après %s tentatives" %(repet))
				tolog_info("-------------- THE END ----------------")
				sys.exit(1)

	# Entrer le numéro du serveur SMS

	rep = send_cmd('AT+CSCA="%s"' %(SMS_server))

	# Passer en mode texte

	rep = send_cmd("AT+CMGF=1")

	# Effacer les SMS présents

#	rep = send_cmd('AT+CMGDA="DEL ALL"')

	tolog_info_verb("...la carte NadHAT fonctionne")

	return()


#---- Nettoyage et arrêt de la carte nadhat

def stop_nadhat():

	tolog_info_verb("Demande d'arrêt de la carte NadHAT...")

	rep = send_cmd("AT+CPOWD=1")
	time.sleep(3)
	pulse(2)

	tolog_info_verb("...la carte NadHAT est arrêtée")

	tolog_bold("-------------- THE END ----------------")

	return()


#---- Envoi de message par SMS

def send_sms(msg, tel_destinataire):

	tolog_bold("Envoi d'un SMS à %s..." %(tel_destinataire))

	if (debug):
		tolog_bold("Mode debug: SMS non envoyé")
	else:
		rep = send_cmd('AT+CMGS="%s"' %(tel_destinataire))
		rep = send_cmd(msg + chr(26))

	rep = send_cmd('AT+CMGDA="DEL SENT"') # Supprime tout SMS envoyé

	tolog_info_verb("...SMS envoyé avec succès")

	return()


#---- Envoi d'un message d'erreur par SMS

def notify_err(msg):
	tolog_err(msg)
	send_sms(msg, tel_admin)
	return()


#---- Lecture des messages SMS

def read_all_sms():
	reply = send_cmd('AT+CMGL="ALL"')
	msg_received = ("READ" in reply)

	return(msg_received, reply)


#---- Effacement du dernier message SMS

def delete_one_sms(msg_rank):

	tolog_info_verb("Effacement du message %s de la file d'attente" %(msg_rank))
	reply = send_cmd('AT+CMGD=' + msg_rank)	# Supprime un SMS lu
	return()


#-------------------------------------------------
# 		Décode des SMS
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

	debut = debut + 7 	# Passer les caractères 'READ","'
	fin = chaine.find('"', debut)
	
	numero = chaine[debut:fin]
	ok = check_tel(numero)
	if not ok:
		tolog_err("Erreur d'interprétation des SMS: num de tel non numérique >>>\n%s" %(chaine))
		return(False, numero, "Erreur interpretation appelant SMS", rank)

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


#---- Extraction de la commande du message

def extract_command(msg_sms):

	tolog_info_verb("Extraction des commandes d'un message...")

	msg_sms = msg_sms.replace('  ', ' ')	# Replace les double espace en simple espace
	
	command_sms = msg_sms.split(' ')

	try :
		command1 = command_sms[0].title()
	except:
		return(False, '')
	
	return(True, command1)



#-------------------------------------------------
# 		Gestion Email
#-------------------------------------------------


#---- Envoi d'email général

def send_email(email, sujet, msg):

	tolog_info("Envoi du mail '%s' à %s..." %(sujet, email))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()

	msgMail = MIMEMultipart()
	msgMail['From'] = addEmailFrom
	msgMail['To'] = email
	msgMail['Subject'] = sujet
	msgMail.add_header('reply-to', addEmailAdm)	# addEmailNPR
	msgMail.attach(MIMEText(msg, 'plain', 'utf-8'))
	body = msgMail.as_string()

	server.login(addEmailFrom, addEmailPass)
	server.sendmail(addEmailFrom, email, body)
	server.quit()

	tolog_info_verb("...envoi de l'email OK")

	return()


#-------------------------------------------------
# 		Utilitaires
#-------------------------------------------------

#---- Action sur command "Restart"

def reboot():

	tolog_info("Détection de demande de reboot système")

	stop_nadhat()

	efface_panic()

	os.system("sudo reboot")	# Boom
	return(True)


#---- Validation du numéro de téléphone d'un message

def check_tel(numero):

	tolog_info_verb("Validation du numéro de téléphone %s..." %(numero))

	if numero.isdigit():
		return(True)

	# Si le numéro n'est pas un nb, essayer de retirer le "+" au début

	if numero[0] != '+':
		return(False)
		
	# Si le numéro n'est pas non plus un nb, erreur de lecture
	
	return (numero[1:].isdigit()) 


#-------------------------------------------------
#--- DEBUT DU PROGRAMME --------------------------
#-------------------------------------------------

if __name__ == "__main__":

	(verbose, debug) = test_verbose(sys.argv)

	tolog_info("Vérification du log...")
	check_log()
	
	tolog_info ("Vérification de l'état du programme %s..." %(nom_commande))

	pid_str = get_pid_str()
	
	if pid_str == '':
		tolog_info_verb("Pas d'identifiant de processus trouvé ; %s correctement arrêté !" %(nom_commande))
		sys.exit(0)
	
	tolog_info_verb("Identifiant de programme %s = %s" %(nom_commande, pid_str))
	
	pid = int(pid_str)
	
	if psutil.pid_exists(pid):
		tolog_info("Processus %s toujours actif !" %(nom_commande))
		sys.exit(0)
	
	tolog_err("Processus %s incorrectement arrêté !" %(pid_str))

	param = read_conf()

	addEmailFrom = param['send_email']
	addEmailPass = param['pass_email']
	SMS_server = param['SMS_server']
	tel_admin = param['tel_admin']
	addEmailAdm = param['addEmailAdm']

	send_email(addEmailAdm, panicEmailSubject, msg_alert)

	nadhat = serial.Serial(
		port = PORT_SERIE,
		baudrate = 9600,
		parity = serial.PARITY_NONE,
		stopbits = serial.STOPBITS_ONE,
		bytesize = serial.EIGHTBITS,
		timeout = 3
	)

	init_nadhat()

	send_sms(msg_alert + msg_restart, tel_admin)
	
	time.sleep(delay_reply)
	
	while True:

		msg_received, reply = read_all_sms()	# Lire les SMS dans la mémoire	
		if not msg_received:		# S'il ne reste aucun SMS à lire
			break
			
		(ok, tel_emetteur, msg_sms, msg_rank) = extract_sms(reply)	# Extraire les données du SMS

		tolog_bold("SMS reçu de %s: %s" %(tel_emetteur, msg_sms))

		delete_one_sms(msg_rank)	# Effacer le SMS lu

	#	Décodage du message

		if (tel_emetteur == tel_admin):
		
			(ok, command) = extract_command(msg_sms)	# décoder la command

			if ok and (command == "!Restart"):	# S'il s'agit d'un ordre de reboot
				send_sms(msg_reboot, tel_admin)
				reboot()

	tolog_info_verb("Pas d'ordre de restart reçu!")
	stop_nadhat()

	efface_panic()
	
	sys.exit(255)

#-------------------------------------------------
#--- FIN DU PROGRAMME ----------------------------
#-------------------------------------------------
