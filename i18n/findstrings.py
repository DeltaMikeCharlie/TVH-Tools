#!/usr/bin/env python
#Script to locate all translatable strings in C, JS and DOCS code and
#reconcile them to the master strings list.
#Definately an example of Spaghetti code.
#DeltaMikeCharlie - Feb 2024

#The questions that this script is trying to answer are:

#1. Are there any strings used by the application that are not known to the translation system?  (In a POT)  These are candidate for new translations.
#====> strings/new_XXXX.txt
#List of strings used by the application but not in the POT.

#====> new_pot_XXXX.txt
#This merges the existing POT with the newly discovered strings.
#It also notes, but leaves in, strings that appear to be disused.

#2. Are there any translation strings that are present in the POT/PO files but not used by the application?  These are candidates for removal.
#====> deletion_candidates.txt

#3. Are there any strings common to the 3 translation areas (C, JS & DOCS) that could maybe share a translation?
#====> usage_summary_by_string_and_POT_type.txt
#====> multiple_usage.txt (Only strings used more than once.)

#4. Are there any translation strings where the differences are so trivial that the 2 strings can be combined into one? (Thanks ukn_unknown)
#====> similarity.txt

#5. Are there any 'translated' foreign strings that just use the English text as their translation?


#NOTE: The BASEDIR must have been built once as this script relies on
#      some artifacts of the build process.
#BASEDIR = "/home/dmc/development/TVH/dvr_errno/tvheadend"
BASEDIR = "/home/dmc/development/TVH/i18n_strings/tvheadend"


import os
import pprint
import re
import difflib
from datetime import datetime

TIMESTAMP = "Generated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")

#print(TIMESTAMP)

#print("{:.2f}".format(1234567895.987654321))

#quit()


#print(difflib.SequenceMatcher(None,"This is a test" ,"This is a test").ratio())  #Ratio = 1.0
#print(difflib.SequenceMatcher(None,"Thus is a test" ,"This is a test").ratio())  #Ratio = 0.9285714285714286
#print(difflib.SequenceMatcher(None,"This is a test" ,"This is a test.").ratio())  #Ratio = 0.9655172413793104
#print(difflib.SequenceMatcher(None,"This is a test!" ,"This is a test?").ratio())  #Ratio = 0.9333333333333333
#print(difflib.SequenceMatcher(None,"I have a pet mouse" ,"I have a pet elephant").ratio())  #Ratio = 0.717948717948718
#print(difflib.SequenceMatcher(None,"My favourite colour is red." ,"My favorite color is red.").ratio())  #Ratio = 0.9615384615384616
#print(difflib.SequenceMatcher(None,"Banana green automotive tree" ,"Sedimentary arterial gateaux procedure").ratio())  #Ratio = 0.21212121212121213
#print(difflib.SequenceMatcher(None,"Bitrate mode" ,"Bitrate mode.").ratio())  #Ratio = 0.96


#Delete a chracter from a string if it is the first and last character.
def topAndTail(inString, char):
	#print(inString, char)
	#if inString[0:1] == char:
	#	print("Got Start")
	#if inString[-1:] == char:
	#	print("Got End")
	if inString[0:1] == char and inString[-1:] == char:
		return inString[1:len(inString)-1]
	else:
		return inString



#junk = "Embedded \"quote\" characters"
#bytes = bytes(junk, 'utf-8')
#junk = bytes.decode('unicode_escape')

#print(junk)

#print(topAndTail('\"\\\"This is a string\\\"\"', "\""))
#print(topAndTail('How now brown cow', "\""))

#quit()


#Chosen because " and ' are used frequently.
#OPENQ = "❯"
#CLOSEQ =  "❮"
OPENQ = ">>"
CLOSEQ =  "<<"

masterList = {}
languageList = []



#Save the string for later reconciliation
#         id - The msgid
#        str - the msgstr
#        src - The source file
# sourceType - C or JS
#      audit - The audit trail
#translation - A Language/translation tuple.

def saveString(id, str, src, sourceType, audit, translation):
	if len(str) == 0:
		str = "{EMPTY}"
	#print("Saving: ", "[" + src + "]", "[" + id + "]", "[" + str + "]")
	if sourceType not in masterList:
		masterList[sourceType] = {}
	if not id in masterList[sourceType]:
		masterList[sourceType][id] = {}
		masterList[sourceType][id]['str'] = ""
		masterList[sourceType][id]['src'] = []
		masterList[sourceType][id]['src_code'] = []
		masterList[sourceType][id]['audit'] = ""
		masterList[sourceType][id]['translations'] = {}
		masterList[sourceType][id]['GB'] = ""
		masterList[sourceType][id]['US'] = ""
	if len(str) != 0:
		masterList[sourceType][id]['str'] = str
	if len(src) !=0:
		if src not in masterList[sourceType][id]['src']:
			masterList[sourceType][id]['src'].append(src)
		if src != "POT" and src.count(".po") == 0:
			if src not in masterList[sourceType][id]['src_code']:
				masterList[sourceType][id]['src_code'].append(src)
		
	if len(audit) !=0:
		if len(masterList[sourceType][id]['audit']) == 0:
			masterList[sourceType][id]['audit'] = audit
		else:
			masterList[sourceType][id]['audit'] = masterList[sourceType][id]['audit'] + "\n" + audit
	if not translation is None:
		#masterList[sourceType][id]['translations'].append(translation)
		#lang, text
		if translation['lang'] not in masterList[sourceType][id]['translations']:
			masterList[sourceType][id]['translations'][translation['lang']] = {}
		masterList[sourceType][id]['translations'][translation['lang']] = translation['text']
		#Store GB and US specially for checking if other
		#translations use these strings.  IE, not really translated.
		if translation['lang'] == "en_GB":
			masterList[sourceType][id]['GB'] = translation['text']
		if translation['lang'] == "en_US":
			masterList[sourceType][id]['US'] = translation['text']


#Read a translation PO file and extract the ID and string.
def OLD_readPO(fileName, sourceType):
	theMode = 0
	theID = ""
	theStr = ""
	savedID = ""
	lineNum = 0
	audit = ""
	fd = open(fileName, "r")
	for line in fd:
		lineNum = lineNum + 1
		auditLine = OPENQ + line.rstrip("\n\r") + CLOSEQ
		line = line.strip()
		if line.find('msgid', 0, 5) != -1:
			if len(theStr) != 0:
				#print("Type: ", sourceType)
				#print("Str: ", theStr)
				saveString(savedID, theStr, "MASTER", sourceType, audit, None)
				theStr = ""
			theMode = 1
			theText = line[7:]
			theText = theText.rstrip(theText[-1])
			theID = theText
			audit = "MASTER_" + sourceType + "[" + str(lineNum) + "] " + auditLine

		if line.find('msgstr', 0, 6) != -1:
			if len(theID) != 0:
				#print(" ID: ", theID)
				savedID = theID
				theID = ""
			theMode = 2
			theText = line[8:]
			theText = theText.rstrip(theText[-1])
			theStr = theText

		if line.find('"', 0, 1) != -1:
			#print("CONT" + str(theMode)+" :", line)
			theText = line[1:]
			theText = theText.rstrip(theText[-1])
			audit = audit +  "\nMASTER_" + sourceType + "[" + str(lineNum) + "] " + auditLine
			if theMode == 1:
				theID = theID + theText
			if theMode == 2:
				theStr = theStr + theText


	fd.close()
	
	#if len(theID) != 0:
	#	print(" ID: ", theID)

	if len(theStr) != 0:
		#print("Str: ", theStr)
		saveString(savedID, theStr, "MASTER", sourceType, audit, None)

#Read a translation PO file and extract the ID and string.
def readPO(OSfileName, fileName, sourceType, language):
	theMode = 0
	theID = ""
	theStr = ""
	savedID = ""
	lineNum = 0
	audit = ""
	tmpText = []
	tmpText.append("")
	tmpText.append("")
	tmpText.append("")
	tmpText[1] = ""
	tmpText[2] = ""
	
	fd = open(OSfileName, "r")
	for line in fd:
		lineNum = lineNum + 1
		auditLine = line
		line = line.strip()
		keyLine = False
		
		if len(line) != 0:
			if line[0:1] == "#": #Filter comments
				line = ""

		if len(line) != 0:

			if line.find('msgid', 0, 5) != -1:

				if theMode == 2:
					tmpTran = {}
					tmpTran['lang'] = language
					tmpTran['text'] = tmpText[2]
					saveString(tmpText[1], theStr, fileName, sourceType, audit, tmpTran)

					#if tmpText[1] != tmpText[2]:
					#	print("!! FOUND ONE!!")
					#print(" MSGID: ", tmpText[1])
					#print("MSGSTR: ", tmpText[2])
					#print(audit)
					tmpText[1] = ""
					tmpText[2] = ""
					audit = ""

				theMode = 1
				line = line[6:].strip()
				#tmpText[1] = line.strip("\'\"")
				tmpText[1] = topAndTail(line, "'")
				tmpText[1] = topAndTail(tmpText[1], '"')
				keyLine = True

			if line.find('msgstr', 0, 6) != -1:
				theMode = 2
				line = line[7:].strip()
				#tmpText[2] = line.strip("\'\"")
				tmpText[2] = topAndTail(line, "'")
				tmpText[2] = topAndTail(tmpText[2], '"')
				keyLine = True

			#If the current line ends in a quote, then we need to wait for a continuation line.
			if (line[-1] == '"' or line[-1] == "'") and keyLine == False:
				tmpText[theMode] = tmpText[theMode] + line.strip("\'\"")

			if len(audit) == 0:
				audit = fileName + "[" + str(lineNum) + "] " + OPENQ + auditLine.rstrip("\r\n") + CLOSEQ
			else:
				audit = audit + "\n" + fileName + "[" + str(lineNum) + "] " + OPENQ + auditLine.rstrip("\r\n") + CLOSEQ


	tmpTran = {}
	tmpTran['lang'] = language
	tmpTran['text'] = tmpText[2]
	saveString(tmpText[1], theStr, fileName, sourceType, audit, tmpTran)

	#if tmpText[1] != tmpText[2]:
	#	print("!! FOUND ONE!!")
	#print(" MSGID_ ", tmpText[1])
	#print("MSGSTR_ ", tmpText[2])
	#print(audit)

	fd.close()



def processC(line, fileName, audit):

	#TODO - count '.name' '.desc' '.ic_caption' as these seem to be related to JSON doco.

	#Look for rogue characters in front
	firstPos = foundPos = line.find('N_(')
	if firstPos != 0:
		line = line[firstPos:]

	cFound = line.count("N_(")
	#print("PROCESSING ", cFound, line)
	#found = re.split(r'N_(', line)
	found = re.split('N_\(', line)
	#print(found)
	for instance in found:
		if len(instance) != 0:
			
			#instance = instance.strip(";,)\"\ ")
			instance = instance.strip("\ ")
			#Do these charactrers one by one.
			instance = instance.rstrip("\ ")
			instance = instance.rstrip(";")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip(",")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip(")")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip("\"")

			foundEnd = instance.count('")')
			foundEscEnd = instance.count('\\")')
			#print(foundEnd, foundEscEnd)
			
			#If we have same rogue characters tacked onto the end of our target function
			if foundEnd - foundEscEnd > 0:
				foundPos = instance.find('")')
				#print(foundPos)
				if foundPos > 0:
					instance = instance[0:foundPos]
			

			instance = instance.strip("\"")
			
			#print("Instance: ", instance)
			if fileName.count("docs_inc.c") == 0:
				saveString(instance, "", fileName, "C", audit, None)
			else:
				saveString(instance, "", fileName, "DOCS", audit, None)


def processJS(line, fileName, audit):
	#NOTE - Some JS string use single quotes, some use double quotes.
	#print("JS", line, fileName)

	#Look for rogue characters in front
	#firstPos = foundPos = line.find('_(')
	firstPos = line.find('_(')
	if firstPos != 0:
		line = line[firstPos:]

	cFound = line.count("_(")
	#print("PROCESSING ", cFound, line)
	#found = re.split(r'N_(', line)
	found = re.split('_\(', line)
	#print(found)
	for instance in found:
		if len(instance) != 0:
			
			#instance = instance.strip(";,)\"\ ")
			instance = instance.strip("\ ")
			#Do these charactrers one by one.
			instance = instance.rstrip("\ ")
			instance = instance.rstrip(";")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip(",")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip(")")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip("\'")
			instance = instance.rstrip("\ ")
			instance = instance.rstrip("\"")

			foundEnd = instance.count('")')
			foundEscEnd = instance.count('\\")')
			#print(foundEnd, foundEscEnd)
			if foundEnd == 0:
				foundEnd = instance.count("')")
			if foundEscEnd == 0:
				foundEscEnd = instance.count("\\')")

			#print(foundEnd, foundEscEnd)
			
			#If we have same rogue characters tacked onto the end of our target function
			if foundEnd - foundEscEnd > 0:
				foundPos = instance.find("')")
				if foundPos < 1:
					foundPos = instance.find('")')
				#print(foundPos)
				if foundPos > 0:
					instance = instance[0:foundPos]
			

			instance = instance.strip('\"')
			instance = instance.strip("\'")
			
			#print("Instance: ", instance)
			saveString(instance, "", fileName, "JS", audit, None)


def checkFile(baseName, fileName, ext):
	fd = open(baseName + fileName, mode="r", encoding="utf-8", errors="backslashreplace")  #Some C source files have non-UTF8 characters.

	fullLine = ""
	lineNum = 0
	audit = ""
	expectingContinuation = False
	for line in fd:
		auditLine = OPENQ + line.rstrip("\n\r") + CLOSEQ
		lineNum = lineNum + 1
		line = line.strip()
		
		jsFound = line.count("_(")
		cFound = line.count("N_(")
		#if cFound > 1:
		#	print("QUITTING", line)
		#	quit()

		#NOTE: JS can have conbtinutation lines as follows
		#    tvheadend.log(_('There seems to be a problem with the '
		#            + 'live update feed from Tvheadend. '
		#            + 'Trying to reconnect...'),
		#            'font-weight: bold; color: #f00');

		if jsFound > 0 and cFound == 0 and ext == ".js":
			processJS(line, fileName, fileName + "[" + str(lineNum) + "] " + auditLine)
			#print(fileName, line, line.count("_("))
			#for i in range(jsFound):
			#	print(i)

		#If 'N_(' is not found AND the line buffer is not empty.
		if line.find("N_(") != -1:
			#Process the saved buffer.
			if len(fullLine) != 0:
				#print("FULL: ", fullLine)
				#print(audit)
				traceName = (baseName + fileName)[len(BASEDIR):]
				#processC(fullLine, fileName, audit)
				processC(fullLine, traceName, audit)
				audit = ""
			#Reset the saved buffer
			fullLine = ""
				
			#print(fileName + "(" + str(lineNum) + ")", "C Count", cFound, line)
			lineSep = "\n"
			if len(audit) == 0:
				lineSep = ""
			audit = audit + lineSep + fileName + "[" + str(lineNum) + "] " + auditLine

			fullLine = line

			#If the last character is a quote, then expect a continuation line to follow.
			if line[-1] == '"':
				expectingContinuation = True

		#In C, strings can extend over multiple lines.  We need to wait until
		#we get the last line before processing the function call.
		if line.find('"', 0, 1) != -1 and len(fullLine) != 0 and expectingContinuation == True:
			#print("C Continuation", line)
			audit = audit + "\n" + fileName + "[" + str(lineNum) + "] " + auditLine
			if fullLine[-1] == '"':
				fullLine = fullLine[:-1]
			fullLine = fullLine + line[1:]

	if len(fullLine) != 0:
		#print("LAST: ", fullLine)
		#print(audit)
		traceName = (baseName + fileName)[len(BASEDIR):]
		#processC(fullLine, fileName, audit)
		processC(fullLine, traceName, audit)
		audit = ""
		fullLine = ""


	fd.close()




#checkFile("/home/dmc/development/TVH/dvr_errno/tvheadend/src/", "config.c")
#checkFile("/home/dmc/development/TVH/dvr_errno/tvheadend/src/", "webui/static/app/dvr.js")

#OLD_readPO(BASEDIR + "/intl/tvheadend.en_GB.po", "C")         #This is only for C strings.
#OLD_readPO(BASEDIR + "/intl/js/tvheadend.js.en_GB.po", "JS")   #This is only for JS strings.

#readPO(BASEDIR + "/intl/tvheadend.en_GB.po", "MASTER", "C", "MASTER_C")         #This is only for C strings.
#readPO(BASEDIR + "/intl/js/tvheadend.js.en_GB.po", "MASTER", "JS", "MASTER_JS")   #This is only for JS strings.
#readPO(BASEDIR + "/intl/docs/tvheadend.doc.en_GB.po", "MASTER", "DOCS", "MASTER_DOCS")   #This is only for DOC strings.

print("Loading language templates.")

#The POT files are the 'Portable Object Template' files used by GNU gettext for i18n.
readPO(BASEDIR + "/intl/tvheadend.pot", "POT", "C", "MASTER_C")         #This is only for C strings.
readPO(BASEDIR + "/intl/js/tvheadend.js.pot", "POT", "JS", "MASTER_JS")   #This is only for JS strings.
readPO(BASEDIR + "/intl/docs/tvheadend.doc.pot", "POT", "DOCS", "MASTER_DOCS")   #This is only for DOC strings.

print("Looking for duplicate strings between types.")
#Now that the master strings have been loaded from POT, look for duplicates between types.
uniqueStrings = {}
for mod in masterList:
	#print(mod)
	for item in masterList[mod]:
		#print(item)
		if item not in uniqueStrings:
			uniqueStrings[item] = {}
			uniqueStrings[item]["C"] = []
			uniqueStrings[item]["JS"] = []
			uniqueStrings[item]["DOCS"] = []
		for src in masterList[mod][item]['src']:
			uniqueStrings[item][mod].append(src)

print("Looking for strings used by more than one module.")
#Write out the string usage summary report by POT type.
count = []
count.append(0)
count.append(0)
count.append(0)
count.append(0)

multiple = open("multiple_usage.txt", "w")
multiple.write(TIMESTAMP + "\n")
multiple.write("Strings used by more than one module.\n\n")

usage = open("usage_summary_by_string_and_POT_type.txt", "w")
usage.write(TIMESTAMP + "\n")
usage.write(str(len(uniqueStrings)) + " unique POT strings in total.\n\n")
for item in uniqueStrings:
	usage.write("String: " + OPENQ + item + CLOSEQ + "\n")
	x = []
	if len(uniqueStrings[item]['C']) != 0:
		x.append("C")
	if len(uniqueStrings[item]['JS']) != 0:
		x.append("JS")
	if len(uniqueStrings[item]['DOCS']) != 0:
		x.append("DOCS")
	usage.write("   Source: " + str(x) + "\n\n")
	
	count[len(x)] = count[len(x)] + 1
	
	if len(x) > 1:
		multiple.write(OPENQ + item + CLOSEQ + "\n\n")
	
	
	#print("     C ", uniqueStrings[item]['C'])
	#print("    JS ", uniqueStrings[item]['JS'])
	#print("  DOCS ", uniqueStrings[item]['DOCS'])


#for N in range(1,4):
#	print(N, count[N])

usage.write("Single occurences: " + str(count[1]) + "\n")
usage.write("Double occurences: " + str(count[2]) + "\n")
usage.write("Triple occurences: " + str(count[3]) + "\n")
usage.close()


multiple.write("Double occurences: " + str(count[2]) + "\n")
multiple.write("Triple occurences: " + str(count[3]) + "\n")
multiple.close()


#A few test cases.
#processC('N_("^Simple test string.^");', 'TEST')
#processC('N_("First string."), rogueFunction("Rogue text"), N_("Second string.");', 'TEST')
#processC('N_("First string."), rogueTwo("Rogue \\") text"), N_("Second string.");', 'TEST')
#processC('N_("First string."), "Literal", N_("Second string.");', 'TEST')
#processC('N_("Escaped \\"test\\" string.");', 'TEST')
#processC('N_("Never use \'N_(\' in a string.");', 'TEST')
#processC('N_("Simple test string.");', 'TEST')
#processC('[LS_THREAD]        = { "thread",        N_("Thread") },', 'TEST')
#processC('C_{ N_("Informational"), N_("Educational"), N_("School programs"), NULL },', 'TEST')
#processC('N_("Ends with a (bracket)");', 'TEST')


#processJS("_('^Simple test string.^');", 'TEST')
#processJS("                  _('Recordings') + '\" : \"' + _('Recording') + '\"]})'", 'TEST')
#processJS('                  _("ZRecordings") + "\' : \'" + _("ZRecording") + "\']})"', 'TEST')
#processJS("_('content += '<div class=\"x-epg-meta\"><font color=\"red\"><span class=\"x-epg-prefix\">' + _('Will be skipped') + '<br>' + _('because it is a rerun of:') + '</span>' + tvheadend.niceDate(duplicate * 1000) + '</font></div>';');", 'TEST')

#quit()

print("Loading source files.")

for root, dirs, files in os.walk(BASEDIR + "/src", topdown=False):
	for name in files:
		#print("FILE: ", os.path.join(root, name))
		#print("FILE: ", root, name)
		fileParts = (os.path.splitext(name))
		ext = fileParts[-1]
		#print("EXT: ", ext)
		#if ext.lower() == ".c" or ext.lower() == ".h" or ext.lower() == ".js":
		if ext.lower() == ".c" or ext.lower() == ".js":
			fullName = os.path.join(root, name)
			#print("FILE: ", root, name)
			#print("FILE: ", fullName)
			#checkFile("", fullName)
			#Docs should not be excluded here.
			#The build process takes in the MD file and
			#creates this C file.
			#if name != "docs_inc.c":
			#if ext.lower() == ".js":
			#	print(name)
			#	quit()
			#traceName = fullName[len(BASEDIR):]
			checkFile(root + "/", name, ext.lower())
			#checkFile(root + "/", traceName, ext.lower())
	#for name in dirs:
	#	#print(" DIR: ", os.path.join(root, name))
	#	print(" DIR: ", root, name)



#pprint.pprint(masterList)


#quit()


print("Producing summaries.")

if not os.path.exists("audit"):
    os.makedirs("audit")

if not os.path.exists("strings"):
    os.makedirs("strings")

mod = "C"

summary = open("audit/summary_c.txt", "w")
newstr = open("strings/new_c.txt", "w")

summary.write("------- " + mod + " Summary --------------------\n")
summary.write(TIMESTAMP + "\n")

newstr.write("------- " + mod + " New Strings --------------------\n")
newstr.write(TIMESTAMP + "\n\n")


masterCount = 0
masterOnly = 0
#docsCount = 0
jsonCount = 0

for item in masterList[mod]:
	#print(item)
	#if len(masterList[item]['src']) > 1:
	#	print(item, masterList[item])

	summary.write("\nString: '" + item + "'\n")
	
	#if "docs_inc.c" in masterList[mod][item]['src']:
	#	docsCount = docsCount + 1
	if "POT" in masterList[mod][item]['src']:
		masterCount = masterCount + 1
		if len(masterList[mod][item]['src']) == 1:
			masterOnly = masterOnly + 1
	
	if "POT" not in masterList[mod][item]['src']:
		summary.write("    *NOT FOUND IN POT\n")
		newstr.write(item + "\n\n")

	if masterList["C"][item]['audit'].count(".name") != 0 or masterList["C"][item]['audit'].count(".desc") != 0 or masterList["C"][item]['audit'].count(".ic_caption") != 0:
		jsonCount = jsonCount + 1

	for name in masterList[mod][item]['src']:
		summary.write("    " + name)
		summary.write("\n")
		#else:
		#	print(masterList[item]['src'], item)
		#	masterCount = masterCount + 1

summary.write("---------------------------\n")

summary.write("      Total Count:" + str(len(masterList[mod])) + "\n")
summary.write("   Count from POT:" + str(masterCount) + "\n")
summary.write("        Shortfall:" + str(len(masterList[mod]) - masterCount) + "\n")
summary.write("Count only in POT:" + str(masterOnly) + "\n")
#summary.write("  Count from Docs:" + str(docsCount) + "\n")
summary.write("Count of JSON API:" + str(jsonCount) + "\n")



mod = "JS"

summary.close()
summary = open("audit/summary_js.txt", "w")
newstr.close()
newstr = open("strings/new_js.txt", "w")

newstr.write("------- " + mod + " New Strings --------------------\n")
newstr.write(TIMESTAMP + "\n\n")


summary.write("------- " + mod + " Summary --------------------\n")
summary.write(TIMESTAMP + "\n")

masterCount = 0;
masterOnly = 0
#docsCount = 0
for item in masterList[mod]:
	#print(item)
	#if len(masterList[item]['src']) > 1:
	#	print(item, masterList[item])

	summary.write("\nString: '" + item + "'\n")
	
	#if "docs_inc.c" in masterList[mod][item]['src']:
	#	docsCount = docsCount + 1
	if "POT" in masterList[mod][item]['src']:
		masterCount = masterCount + 1
		if len(masterList[mod][item]['src']) == 1:
			masterOnly = masterOnly + 1
	
	if "POT" not in masterList[mod][item]['src']:
		summary.write("    *NOT FOUND IN POT\n")
		newstr.write(item + "\n\n")

	for name in masterList[mod][item]['src']:
		summary.write("    " + name)
		summary.write("\n")
		#else:
		#	print(masterList[item]['src'], item)
		#	masterCount = masterCount + 1

summary.write("---------------------------\n")

summary.write("      Total Count:" + str(len(masterList[mod])) + "\n")
summary.write("   Count from POT:" + str(masterCount) + "\n")
summary.write("        Shortfall:" + str(len(masterList[mod]) - masterCount) + "\n")
summary.write("Count only in POT:" + str(masterOnly) + "\n")
#summary.write("  Count from Docs:" + str(docsCount) + "\n")

mod = "DOCS"

summary.close()
summary = open("audit/summary_docs.txt", "w")
newstr.close()
newstr = open("strings/new_docs.txt", "w")

newstr.write("------- " + mod + " New Strings --------------------\n")
newstr.write(TIMESTAMP + "\n\n")


summary.write("------- " + mod + " Summary --------------------\n")
summary.write(TIMESTAMP + "\n")

masterCount = 0;
masterOnly = 0
#docsCount = 0
for item in masterList[mod]:
	#print(item)
	#if len(masterList[item]['src']) > 1:
	#	print(item, masterList[item])

	summary.write("\nString: '" + item + "'\n")
	
	#if "docs_inc.c" in masterList[mod][item]['src']:
	#	docsCount = docsCount + 1
	if "POT" in masterList[mod][item]['src']:
		masterCount = masterCount + 1
		if len(masterList[mod][item]['src']) == 1:
			masterOnly = masterOnly + 1
	
	if "POT" not in masterList[mod][item]['src']:
		summary.write("    *NOT FOUND IN POT\n")
		newstr.write(item + "\n\n")

	for name in masterList[mod][item]['src']:
		summary.write("    " + name)
		summary.write("\n")
		#else:
		#	print(masterList[item]['src'], item)
		#	masterCount = masterCount + 1

summary.write("---------------------------\n")

summary.write("      Total Count:" + str(len(masterList[mod])) + "\n")
summary.write("   Count from POT:" + str(masterCount) + "\n")
summary.write("        Shortfall:" + str(len(masterList[mod]) - masterCount) + "\n")
summary.write("Count only in POT:" + str(masterOnly) + "\n")
#summary.write("  Count from Docs:" + str(docsCount) + "\n")

#print("-------- Checking C & JS -------------------")
#bothCount = 0
#for item in masterList["C"]:
#	if item in masterList['JS']:
#		print("String", "'" + item + "'", "in both C and JS POT files.")
#		bothCount = bothCount + 1
#print("---------------------------")
#print("     Both Count:", bothCount)

summary.close()


print("Printing consolidate string usage.")

#Write out the consolidated string usage summary report by POT type.
usage = open("consolidated_string_usage.txt", "w")
usage.write(TIMESTAMP + "\n")
usage.write("Consolidated (C + JS + DOCS) list of every string string used,\n")
usage.write("showing the file[line] that refer to that string.\n")
usage.write("Any strings only found in 'POT' are not used by the application.\n\n")

for item in uniqueStrings:
	usage.write("String: " + OPENQ + item + CLOSEQ + "\n")

	if len(uniqueStrings[item]['C']) != 0:
		usage.write("C source files & locations.\n")
		if 'src' in masterList["C"][item]:
			usage.write(str(masterList["C"][item]['src']) + "\n")
		if 'audit' in masterList["C"][item]:
			usage.write(masterList["C"][item]['audit'] + "\n")
	if len(uniqueStrings[item]['JS']) != 0:
		usage.write("JS source files & locations.\n")
		if 'src' in masterList["JS"][item]:
			usage.write(str(masterList["JS"][item]['src']) + "\n")
		if 'audit' in masterList["JS"][item]:
			usage.write(masterList["JS"][item]['audit'] + "\n")
	if len(uniqueStrings[item]['DOCS']) != 0:
		usage.write("DOCS source files & locations.\n")
		if 'src' in masterList["DOCS"][item]:
			usage.write(str(masterList["DOCS"][item]['src']) + "\n")
		if 'audit' in masterList["DOCS"][item]:
			usage.write(masterList["DOCS"][item]['audit'] + "\n")
	
	usage.write("=================================\n")

usage.close()

print("Reporting deletion candidates.")

#Write out a list of deletion candidates.
usage = open("deletion_candidates.txt", "w")
usage.write(TIMESTAMP + "\n")
usage.write("Deletion candidates - Strings that are only present in a POT file,\n")
usage.write("and not found in any C, JS or DOCS files.\n\n")

for item in uniqueStrings:

	flag = False
	if item in masterList["C"]:
		if len(masterList["C"][item]['src']) == 1 and "POT" in masterList["C"][item]['src']:
			flag = True
	if item in masterList["JS"]:
		if len(masterList["JS"][item]['src']) == 1 and "POT" in masterList["JS"][item]['src']:
			flag = True
	if item in masterList["DOCS"]:
		if len(masterList["DOCS"][item]['src']) == 1 and "POT" in masterList["DOCS"][item]['src']:
			flag = True

	if flag == True:

		usage.write("String: " + OPENQ + item + CLOSEQ + "\n")

		if len(uniqueStrings[item]['C']) != 0:
			usage.write("C source files & locations.\n")
			if 'src' in masterList["C"][item]:
				usage.write(str(masterList["C"][item]['src']) + "\n")
			if 'audit' in masterList["C"][item]:
				usage.write(masterList["C"][item]['audit'] + "\n")
		if len(uniqueStrings[item]['JS']) != 0:
			usage.write("JS source files & locations.\n")
			if 'src' in masterList["JS"][item]:
				usage.write(str(masterList["JS"][item]['src']) + "\n")
			if 'audit' in masterList["JS"][item]:
				usage.write(masterList["JS"][item]['audit'] + "\n")
		if len(uniqueStrings[item]['DOCS']) != 0:
			usage.write("DOCS source files & locations.\n")
			if 'src' in masterList["DOCS"][item]:
				usage.write(str(masterList["DOCS"][item]['src']) + "\n")
			if 'audit' in masterList["DOCS"][item]:
				usage.write(masterList["DOCS"][item]['audit'] + "\n")
		
		usage.write("=================================\n")

usage.close()

print("Creating new POT files.")

#Write out the proposed POT files with annotations

if not os.path.exists("intl"):
    os.makedirs("intl")

for mod in masterList:

	if not os.path.exists("intl/" + mod):
	    os.makedirs("intl/" + mod)

	#fn = "new_pot_" + mod + ".txt"
	fn = "intl/" + mod + "/tvheadend.pot"
	pot = open(fn, "w")
	pot.write("#" + TIMESTAMP + "\n\n")
	for item in masterList[mod]:
		if len(masterList[mod][item]['src']) == 1 and 'POT' in masterList[mod][item]['src']:
			pot.write("# NOTE: Potential deletion candidate.  Not used in the application.\n")

		if len(masterList[mod][item]['src']) != 0 and 'POT' not in masterList[mod][item]['src']:
			pot.write("# NOTE: New string.\n")

		pot.write("# " + str(masterList[mod][item]['src']).strip("[]") + "\n")
		pot.write("msgid " + '"' + item + '"' + "\n")
		pot.write("msgstr " + '""\n\n')
	pot.close()
#quit()
print("Loading all language files.")

#Load ALL translated language files

for root, dirs, files in os.walk(BASEDIR + "/intl", topdown=False):
	for name in files:
		lang = name.replace(".pot", "")
		lang = name.replace(".po", "")
		lang = lang.replace("tvheadend.", "")
			
		mod = "C"
		if lang.count("js.") != 0:
			mod = "JS"
			lang = lang.replace("js.", "")
		if lang.count("doc.") != 0:
			mod = "DOCS"
			lang = lang.replace("doc.", "")

		lang = lang.replace("doc.", "")
		lang = lang.replace("js.", "")

		#print(lang, name)

		fileParts = (os.path.splitext(name))
		ext = fileParts[-1]
		if ext.lower() == ".po":
			fullName = os.path.join(root, name)
			#print(lang,"   ",mod, "   ", name, fullName)
			readPO(fullName, name, mod, lang)
			if lang not in languageList:
				languageList.append(lang)


#print("  PO List:", len(masterList))
#pprint.pprint(masterList, indent=4, width=200)
#quit()

#print(str(languageList))


print("Writing audit trails.")

#Write an audit trail with all strings from all
#applications sources and language translations.

counter = 0
c_audit = open("audit/audit_c.txt", "w")
c_audit.write("------- C Audit Trail --------------------\n")
c_audit.write(TIMESTAMP + "\n")
for item in masterList["C"]:
	counter = counter + 1
	c_audit.write("Found string #" + str(counter) + ": " + OPENQ + item + CLOSEQ + "\n")
	c_audit.write(masterList["C"][item]['audit'] + "\n")
	sources = ""
	if "POT" not in masterList["C"][item]['src']:
		sources = "NOT IN MASTER POT "
	sources = sources + str(masterList["C"][item]['src'])
	if len(masterList["C"][item]['src']) == 1 and "POT" in masterList["C"][item]['src']:
		sources = sources + " <<< Only found in master.  String may be disused."

	c_audit.write(sources + "\n")
	if item in masterList['JS']:
		c_audit.write("String also present in JS translations.\n")
		if 'audit' in masterList['JS'][item]:
			c_audit.write(masterList["JS"][item]['audit'] + "\n")
	if item in masterList['DOCS']:
		c_audit.write("String also present in DOCS translations.\n")
		if 'audit' in masterList['DOCS'][item]:
			c_audit.write(masterList["DOCS"][item]['audit'] + "\n")

	c_audit.write("=================================\n\n")
c_audit.write("---------------------------\n")

c_audit.close()


counter = 0
js_audit = open("audit/audit_js.txt", "w")
js_audit.write("------- JS Audit Trail --------------------\n")
js_audit.write(TIMESTAMP + "\n")
for item in masterList["JS"]:
	counter = counter + 1
	js_audit.write("Found string #" + str(counter) + ": " + OPENQ + item + CLOSEQ + "\n")
	js_audit.write(masterList["JS"][item]['audit'] + "\n")
	sources = ""
	if "POT" not in masterList["JS"][item]['src']:
		sources = "NOT IN MASTER POT "
	sources = sources + str(masterList["JS"][item]['src'])
	if len(masterList["JS"][item]['src']) == 1 and "POT" in masterList["JS"][item]['src']:
		sources = sources + " <<< Only found in master.  String may be disused."

	js_audit.write(sources + "\n")
	if item in masterList['C']:
		js_audit.write("String also present in C translations.\n")
		if 'audit' in masterList['C'][item]:
			js_audit.write(masterList["C"][item]['audit'] + "\n")
	if item in masterList['DOCS']:
		js_audit.write("String also present in DOCS translations.\n")
		if 'audit' in masterList['DOCS'][item]:
			js_audit.write(masterList["DOCS"][item]['audit'] + "\n")

	js_audit.write("=================================\n\n")
js_audit.write("---------------------------\n")

js_audit.close()


counter = 0
docs_audit = open("audit/audit_docs.txt", "w")
docs_audit.write("------- DOCS Audit Trail --------------------\n")
docs_audit.write(TIMESTAMP + "\n")
for item in masterList["DOCS"]:
	counter = counter + 1
	docs_audit.write("Found string #" + str(counter) + ": " + OPENQ + item + CLOSEQ + "\n")
	docs_audit.write(masterList["DOCS"][item]['audit'] + "\n")
	sources = ""
	if "POT" not in masterList["DOCS"][item]['src']:
		sources = "NOT IN MASTER POT "
	sources = sources + str(masterList["DOCS"][item]['src'])
	if len(masterList["DOCS"][item]['src']) == 1 and "POT" in masterList["DOCS"][item]['src']:
		sources = sources + " <<< Only found in master.  String may be disused."

	docs_audit.write(sources + "\n")
	if item in masterList['C']:
		docs_audit.write("String also present in C translations.\n")
		if 'audit' in masterList['C'][item]:
			docs_audit.write(masterList["C"][item]['audit'] + "\n")
	if item in masterList['JS']:
		docs_audit.write("String also present in JS translations.\n")
		if 'audit' in masterList['JS'][item]:
			docs_audit.write(masterList["JS"][item]['audit'] + "\n")

	docs_audit.write("=================================\n\n")
docs_audit.write("---------------------------\n")

docs_audit.close()

print("Analysing English text.")

#Analyse English text

rpt = open("english_comparison.txt", "w")
rpt.write("------- GB/US Analysis --------------------\n")
rpt.write("Either language must contain a msgstr translation.\n")
rpt.write(TIMESTAMP + "\n")


bothCount = 0

for mod in masterList:
	for item in masterList[mod]:

		if len(masterList[mod][item]['GB']) != 0 or len(masterList[mod][item]['US']) != 0:
			if (len(masterList[mod][item]['GB']) != 0 and item != masterList[mod][item]['GB']) or (len(masterList[mod][item]['US']) != 0 and item != masterList[mod][item]['US']):
				gb = "="
				if item != masterList[mod][item]['GB']:
					gb = "*"
				us = "="
				if item != masterList[mod][item]['US']:
					us = "*"

				rpt.write("\n" + mod + "\n")
				rpt.write("     " +  OPENQ + item + CLOSEQ + "\n")
				rpt.write("" + gb + "GB: " + OPENQ + masterList[mod][item]['GB'] + CLOSEQ + "\n")
				rpt.write("" + us + "US: " + OPENQ + masterList[mod][item]['US'] + CLOSEQ + "\n")
				rpt.write("     " + str(masterList[mod][item]['src_code']) + "\n")

			if (len(masterList[mod][item]['GB']) != 0 and item == masterList[mod][item]['GB']) and (len(masterList[mod][item]['US']) != 0 and item == masterList[mod][item]['US']):
				#rpt.write("\n" + mod + "\n")
				#rpt.write("     " +  OPENQ + item + CLOSEQ + "\n")
				#rpt.write("      Both languages contain the same text as the msgid.\n")
				bothCount = bothCount + 1
			
rpt.write("\n")
rpt.write("      Both Count:" + str(bothCount) + "\n")

rpt.close()

print("Writing language files.")

if not os.path.exists("intl"):
    os.makedirs("intl")

languageTally = {}

languageList.sort()

for lang in languageList:
	#print(lang)

	if lang not in languageTally:
		languageTally[lang] = {}
	    
	for mod in masterList:

		if mod not in languageTally[lang]:
			languageTally[lang][mod] = {}
			languageTally[lang][mod] = 0


		if not os.path.exists("intl/" + mod):
		    os.makedirs("intl/" + mod)

		langFile = "intl/" + mod + "/tvheadend." + lang + ".po"
		#print("   Writing language file '" + langFile + "'")
		#print(lang, mod)
		#for item in masterList[mod]:
		#	print(lang, mod, item)

		po = open(langFile, "w")
		po.write("#" + TIMESTAMP + "\n\n")
		for item in masterList[mod]:
			#if len(masterList[mod][item]['src']) == 1 and 'POT' in masterList[mod][item]['src']:
			#	po.write("# NOTE: Potential deletion candidate.  Not used in the application.\n")


			#po.write("# " + str(masterList[mod][item]['src_code']).strip("[]") + "\n")
			if len (masterList[mod][item]['src_code']) != 0:
				for src in masterList[mod][item]['src_code']:
					po.write("# " + src + "\n")

			if len(masterList[mod][item]['src']) != 0 and 'POT' not in masterList[mod][item]['src']:
				po.write("# NOTE: New string.\n")

			foreign = ""
			if lang in masterList[mod][item]['translations']:
				foreign = masterList[mod][item]['translations'][lang]

			if lang not in masterList[mod][item]['translations']:
				po.write("# NOTE: id not in current translation.\n")

			if item == foreign:
				po.write("# NOTE: Removed str identical to id.\n")
				foreign = ""

			if lang != "en_GB" and lang != "en_US" and len(foreign) != 0:
				if  (len(masterList[mod][item]["GB"]) != 0 and foreign == masterList[mod][item]["GB"]) or (len(masterList[mod][item]["US"]) != 0 and foreign == masterList[mod][item]["US"]):

					po.write("# NOTE: Removed str matching the GB/US str.\n")
					foreign = ""


			po.write("msgid " + '"' + item + '"' + "\n")


			if len(foreign) != 0:
				po.write("msgstr " + '"' + foreign + '"\n\n')
				languageTally[lang][mod] = languageTally[lang][mod] + 1
			else:
				po.write("msgstr " + '""\n\n')

		po.close()


#Output translation the percentage complete for each language.
print("Translation percentage completeness.")

totC = len(masterList['C']) / 100
totJS = len(masterList['JS']) / 100
totDOCS = len(masterList['DOCS']) / 100

perc = open("percent_translated.txt", "w")

perc.write(TIMESTAMP + "\n")
perc.write("Translation percentage completeness\n\n")


perc.write(("").rjust(8," ") + ("C").rjust(8," ") + ("JS").rjust(8," ") + ("DOCS").rjust(8," ") + "\n")
#perc.write(("Count").rjust(8," ") + str(totC*100).rjust(8," ") + str(totJS*100).rjust(8," ") + str(totDOCS*100).rjust(8," ") + "\n\n")
perc.write(("Count").rjust(8," ") + "{:.0f}".format(totC*100).rjust(8," ") + "{:.0f}".format(totJS*100).rjust(8," ") + "{:.0f}".format(totDOCS*100).rjust(8," ") + "\n\n")


#totC = 1
#totJS = 1
#totDOCS = 1

#totC = totC / 100
#totJS = totJS / 100
#totDOCS = totDOCS / 100


for lang in languageTally:
	#print(len(masterList['C']))
	#print(len(masterList['JS']))
	#print(len(masterList['DOCS']))

	#print(lang.rjust(8," "), str(round(languageTally[lang]['C']/totC,2)).rjust(8," "), str(round(languageTally[lang]['JS']/totJS,2)).rjust(8," "), str(round(languageTally[lang]['DOCS']/totDOCS,2)).rjust(8," "))

	perc.write(lang.rjust(8," ") + str("{:.2f}".format(languageTally[lang]['C']/totC,2)).rjust(8," ") + str("{:.2f}".format(languageTally[lang]['JS']/totJS,2)).rjust(8," ") + str("{:.2f}".format(languageTally[lang]['DOCS']/totDOCS,2)).rjust(8," ") + "\n")

	#for mod in languageTally[lang]:
	#	print(lang, mod, languageTally[lang][mod])


perc.close()


#Normally exit here because the similarity analysis takes a long time.
#quit()


print("Similarity Analysis.")

def checkSimilar():
	for N in range(T):
		#print(N, tmpList[N])
		for NN in range(N+1,T):
			#print(N, NN)
			ratio = difflib.SequenceMatcher(None,tmpList[N] ,tmpList[NN]).ratio()
			if ratio > 0.95 and ratio != 1.0:
				similar.write("SIMILAR (" + str(ratio) + ") : >>" + tmpList[N]  + "<<\n")
				similar.write("SIMILAR (" + str(ratio) + ") : >>" + tmpList[NN]  + "<<\n\n")
				
				if tmpList[N] in masterList["C"]:
					if len(uniqueStrings[tmpList[N]]['C']) != 0:
						similar.write("C source files & locations.\n")
						if 'src' in masterList["C"][tmpList[N]]:
							similar.write(str(masterList["C"][tmpList[N]]['src']) + "\n")
						if 'audit' in masterList["C"][tmpList[N]]:
							similar.write(masterList["C"][tmpList[N]]['audit'] + "\n")
				if tmpList[N] in masterList["JS"]:
					if len(uniqueStrings[tmpList[N]]['C']) != 0:
						similar.write("JS source files & locations.\n")
						if 'src' in masterList["JS"][tmpList[N]]:
							similar.write(str(masterList["JS"][tmpList[N]]['src']) + "\n")
						if 'audit' in masterList["JS"][tmpList[N]]:
							similar.write(masterList["JS"][tmpList[N]]['audit'] + "\n")
				if tmpList[N] in masterList["DOCS"]:
					if len(uniqueStrings[tmpList[N]]['C']) != 0:
						similar.write("DOCS source files & locations.\n")
						if 'src' in masterList["DOCS"][tmpList[N]]:
							similar.write(str(masterList["DOCS"][tmpList[N]]['src']) + "\n")
						if 'audit' in masterList["DOCS"][tmpList[N]]:
							similar.write(masterList["DOCS"][tmpList[N]]['audit'] + "\n")
							
				similar.write("\n")

				if tmpList[NN] in masterList["C"]:
					if len(uniqueStrings[tmpList[NN]]['C']) != 0:
						similar.write("C source files & locations.\n")
						if 'src' in masterList["C"][tmpList[NN]]:
							similar.write(str(masterList["C"][tmpList[NN]]['src']) + "\n")
						if 'audit' in masterList["C"][tmpList[NN]]:
							similar.write(masterList["C"][tmpList[NN]]['audit'] + "\n")
				if tmpList[NN] in masterList["JS"]:
					if len(uniqueStrings[tmpList[NN]]['C']) != 0:
						similar.write("JS source files & locations.\n")
						if 'src' in masterList["JS"][tmpList[NN]]:
							similar.write(str(masterList["JS"][tmpList[NN]]['src']) + "\n")
						if 'audit' in masterList["JS"][tmpList[NN]]:
							similar.write(masterList["JS"][tmpList[NN]]['audit'] + "\n")
				if tmpList[NN] in masterList["DOCS"]:
					if len(uniqueStrings[tmpList[NN]]['C']) != 0:
						similar.write("DOCS source files & locations.\n")
						if 'src' in masterList["DOCS"][tmpList[NN]]:
							similar.write(str(masterList["DOCS"][tmpList[NN]]['src']) + "\n")
						if 'audit' in masterList["DOCS"][tmpList[NN]]:
							similar.write(masterList["DOCS"][tmpList[NN]]['audit'] + "\n")


				similar.write("=================================\n\n")


similar = open("similarity.txt", "w")


#Similarity analysis
#difflib.SequenceMatcher(None,"This is a test" ,"This is a test").ratio()

similar.write("Similarity analysis\n")
similar.write(TIMESTAMP + "\n")

tmpList = []
for item in uniqueStrings:
	tmpList.append(item)
T = len(tmpList)
similar.write(str(T) + " strings compared.\n\n")

checkSimilar()

similar.close()


quit()





