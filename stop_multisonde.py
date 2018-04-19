#!/usr/bin/python
# -*- coding: utf-8 -*-

#---------------------------------------------------#
#													#
#				stop_multisonde.py					#
#													#
#---------------------------------------------------#

# Version: 3/1/18
#
# Programme Python destiné à arrêter le programme receive_multi_sms.py
#
# Usage: sudo ./stop_multisonde.py [-v] &
# 	-v : Mode verbose
#

#-------------------------------------------------
#--- IMPORTS & DEFINITIONS -----------------------
#-------------------------------------------------

import time, sys
import os
import time
import psutil

# Fichiers et constantes

path_filename = '/home/pi/MonitoringSMS/'
log_filename = 'log_multisonde.log'
bootdata_filename = 'time_multisonde.txt'
nom_commande = 'multisonde.py'


bold = '\033[1m'
warning = '\033[91m' # "\x1B[31;40m" # 
normal = '\033[00m'
underline = '\033[94m'

#-------------------------------------------------
#--- PROCEDURES ----------------------------------
#-------------------------------------------------

#---- Mode verbose ? (option "-v")

def test_verbose(arg):

	if len(arg) < 2:
		return(False)
		
	return (arg[1] == "-v")


#---- Envoi des information vers le log

def tolog(txt):
	now = time.strftime('%Y/%m/%d %H:%M:%S')
	msg = "%s\t%s" % (now, txt)
	file = open(path_filename + log_filename, 'a')
	file.write(msg + "\n")
	file.close()
	return()

def tolog_info(text):
	if verbose:
		print("INFO\tSTOP: " + text)
	tolog("INFO\tSTOP: " + text)
	return()

def tolog_info_verb(text):
	if verbose:
		print("Info\tSTOP: " + text)
		tolog("Info\tSTOP: " + text)
	return()

def tolog_err(text):
	if verbose:
		print(warning + "ERR\tSTOP: " + text + normal)
	tolog("ERR\tSTOP: " + text)
	return()

def tolog_bold(text):
	if verbose:
		print(bold + time.strftime('%H:%M:%S') + "\t" + text + normal)
	tolog("INFO\t" + text)
	return()


#---- Extraction de l'identifiant à partir du fichier

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

	if verbose:
		tolog("INFO\tEffacement du fichier panic...")

	if os.path.isfile(full_bootdata_filename):
		os.remove(full_bootdata_filename)

	if verbose:
		tolog("INFO\t...fichier panic effacé")

	return()

#-------------------------------------------------
#--- DEBUT DU PROGRAMME --------------------------
#-------------------------------------------------

if __name__ == "__main__":

	verbose = test_verbose(sys.argv)
	
	tolog_bold("==== Debut du programme d'arrêt de %s =====" %(nom_commande))
	
	tolog_info("Ordre d'arrêt du programme %s..." %(nom_commande))

	pid_str = get_pid_str()
	
	if pid_str == '':
		tolog_err("Pas d'identifiant de processus trouvé ; %s arrêté ?" %(nom_commande))
		tolog_bold("==== Fin du programme d'arrêt de %s =====" %(nom_commande))
		sys.exit(255)
	else:
		tolog_info_verb("Identifiant de programme %s = %s" %(nom_commande, pid_str))
	
	pid = int(pid_str)
	commande = 'sudo kill -2 ' + pid_str
	tolog_info ("...envoi de l'ordre d'arrêt du programme %s de PID = %s" %(nom_commande, pid_str))
	
	if not psutil.pid_exists(pid):
		tolog_err ("Processus %s déjà arrêté !?" %(pid_str))
		efface_panic()
		tolog_info_verb("Fichier panic supprimé")
		tolog_bold("==== Fin du programme d'arrêt de %s =====" %(nom_commande))
		sys.exit(0)
	
	os.system(commande)
	
	while(psutil.pid_exists(pid)):
#		tolog ("INFO\tProcessus %s toujours actif..." %(pid))
		time.sleep(1)

	tolog_info_verb("Programme %s arrêté avec succès !" %(nom_commande))
	tolog_bold("==== Fin du programme d'arrêt de %s =====" %(nom_commande))
	sys.exit(0)

#-------------------------------------------------
#--- FIN DU PROGRAMME ----------------------------
#-------------------------------------------------
