import subprocess
import os
import re
import shutil
import tempfile

assignmentPath = "FacsimileAssignment.zip"

#TODO: actually read test cases from file
testCases = { #input : expected output
    1 : 2,
    2 : 3,
    5 : 6,
    7 : 8
    }

#Unzip assignment
if (not os.path.exists("Temp")):
    os.mkdir("Temp") #make the temp folder, if it doesn't exist already
    #this folder will be the destination of extracted files from the assignment
subprocess.run("tar -xf "+assignmentPath+" -C Temp") #unzip assignment into temp

def runPythonTests(filePath):
    #somehow, all my attempts to give input are causing eoferror
    #apparently input raises this whenever it hits eof, but it shouldn't be hitting that until processing all of my test cases
    
    #use a temporary file as the input stream to the subprocess
    with tempfile.TemporaryFile() as inputBuffer:
        #write all test cases to the input stream
        for item in testCases:
            inputBuffer.write(bytes(str(item), "UTF-8")) #files being tested are probably using input() which requests a string, but stdin expects bytes to be written to it
        #run the subprocess, with stdin as the input stream
        runningFile = subprocess.Popen("py \""+filePath+"\"", stdin=inputBuffer, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #capture stdout into a new temp file
        print("Subprocess: " + str(runningFile.stdout.read())) #TODO: replace with actual read
        runningFile.terminate() #when we're out of test cases, we're done

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
        runPythonTests(os.path.abspath(pythonFiles[0]))
    else:
        print("Could not run project in "+studentFolder.name)
        print(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
        #TODO: add interface to specify which file is desired
    

shutil.rmtree("Temp")