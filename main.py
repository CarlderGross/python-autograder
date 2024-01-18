import subprocess
import os
import re

assignmentPath = "FacsimileAssignment.zip"

if (not os.path.exists("Temp")):
    os.mkdir("Temp") #make the temp folder, if it doesn't exist already
    #this folder will be the destination of extracted files from the assignment

#unzip assignment into temp folder
subprocess.run("tar -xf "+assignmentPath+" -C Temp")

def runPythonFile(filePath):
    subprocess.run("py \""+filePath+"\"")

#TODO: REPLACE PSEUDOCODE
for studentFolder in os.scandir("Temp"):
    #print(studentFolder)
    #find the most recent revision
    latestRevision = None
    for revisionFolder in os.scandir(studentFolder):
        #second element will always be revision number ("Revision 1 - On time")
        if ((latestRevision == None) or (int(revisionFolder.name.split()[1]) > latestRevision.name.split()[1])):  
            latestRevision = revisionFolder
    #get the file inside the folder
    pythonFiles = []
    for file in os.scandir(latestRevision):
        print(file.name)
        if (re.match(".*\\.py", file.name)): #must escape backslash to allow it to appear in regex string
            pythonFiles.append(file)
    if (0 < len(pythonFiles) < 2):
        runPythonFile(os.path.abspath(pythonFiles[0]))
    else:
        print(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
        #TODO: add interface to specify which file is desired
    

#TODO: empty the temp folder after use