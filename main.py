import subprocess
import os
import re
import tempfile

assignmentPath = "FacsimileAssignment.zip"

#TODO: actually read test cases from file
testCases = { #input : expected output
    1 : 2,
    2 : 3,
    5 : 6,
    7 : 8
    }

def runPythonTests(filePath):
    #somehow, all my attempts to give input are causing eoferror
    #apparently input raises this whenever it hits eof, but it shouldn't be hitting that until processing all of my test cases
    
    #write all test cases to the input string
    inputBuffer = ""
    for item in testCases:
        inputBuffer += str(item)+"\n" #files being tested are probably using input() which requests a string, but stdin expects bytes to be written to it
        #run the subprocess, with stdin as the input stream
    runningFile = subprocess.Popen("py \""+filePath+"\"", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    output = runningFile.communicate(inputBuffer) #will be a tuple, with the second value as None
    #anything using normal python input (which is most things) will throw EOFError after all test cases have been read; this is probably fine
    return output[0]

with tempfile.TemporaryDirectory() as Temp:
    #Unzip assignment
    subprocess.run("tar -xf "+assignmentPath+" -C "+os.path.abspath(Temp))
    
    for studentFolder in os.scandir(Temp):
        #find the most recent revision
        latestRevision = None
        for revisionFolder in os.scandir(studentFolder):
            #second element will always be revision number ("Revision 1 - On time")
            if ((latestRevision == None) or (int(revisionFolder.name.split()[1]) > latestRevision.name.split()[1])):  
                latestRevision = revisionFolder
        #get the file inside the folder
        pythonFiles = []
        for file in os.scandir(latestRevision):
            if (re.match(".*\\.py", file.name)): #must escape backslash to allow it to appear in regex string
                pythonFiles.append(file)
        if (0 < len(pythonFiles) < 2):
            result = runPythonTests(os.path.abspath(pythonFiles[0]))
            #identify which parts are the hardcoded prompts and which parts are the actual output
            #this is done by reading the code directly and identifying strings in input blocks
            inputPrompts = []
            for file in pythonFiles:
                with open(file, 'r') as codeFile:
                    for line in codeFile:
                        inputIndex = line.find("input(")
                        if (inputIndex >= 0):
                            p_string = line[inputIndex:]
                            endParen = p_string.find(")")
                            p_string = p_string[6:endParen]
                            if (p_string[0] == "\"" and p_string[-1] == "\""): #if the interior of the input() was a direct string rather than a variable
                                p_string.strip() #strip whitespace
                                p_string = p_string[1:-1] #remove first and last characters (quotation marks)
                                inputPrompts.append(p_string) #we have now identified one of the input prompts
            promptPattern = ""
            for prompt in inputPrompts:
                promptPattern += ""+prompt+"|"
            promptPattern = promptPattern[0:len(promptPattern)-1] #delete the last extraneous separator, add parens
            #print(promptPattern)
            #promptPattern = re.compile(promptPattern)
            if (promptPattern):
                result = re.split(promptPattern, result) #split the string along all known input prompts, leaving only the outputs
            print(result)
            #TODO: parse the results
        else:
            #TODO: preferentially run main.py or projectname.py before asking for help
            print("Could not run project in "+studentFolder.name)
            print(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
            #TODO: add interface to specify which file is desired