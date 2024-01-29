import subprocess
import os
import re
import tempfile

assignmentPath = "FacsimileAssignment.zip"

#TODO: actually read test cases from file
testCases = { #input : expected output, stored as tuples because there may be more than one
    (1,) : ("2",),
    (2,) : ("3",),
    (5,) : ("6",),
    (7,) : ("8",)
    }

def runPythonTests(filePath):
    outputs = []
    for inputs in testCases:
        #run the program separately for each test case, since we can't be sure that it will infinitely accept inputs
        inputBuffer = ""
        for item in inputs:
            inputBuffer += str(item)+"\n" #files being tested are probably using input() which requests a string, but stdin expects bytes to be written to it
            #run the subprocess, with stdin as the input stream
        runningFile = subprocess.Popen("py \""+filePath+"\"", stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        output = runningFile.communicate(inputBuffer) #will be a tuple, with the second value as None
        #anything using normal python input (which is most things) will throw EOFError after all test cases have been read; this is probably fine
        outputs.append(output[0])
    return outputs

def inputPromptPattern(file): #parses a python file, and returns a regex pattern to match all string literals passed as the prompt to input() blocks
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
    promptPattern = promptPattern[0:len(promptPattern)-1] #delete the last extraneous separator
    return promptPattern

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
            results = runPythonTests(os.path.abspath(pythonFiles[0]))
            #identify which parts are the hardcoded prompts and which parts are the actual output
            promptPattern = inputPromptPattern(file)
            for index, result in enumerate(results):
                expectedOut = list(testCases.values())[index]
                if (promptPattern):
                    result = re.split(promptPattern, result) #split the string along all known input prompts, leaving only the outputs
                    for i, item in enumerate(result): #clean the results of excess newlines
                        result[i] = item.strip()
                    tup_result = tuple(result[1:len(expectedOut)+1])
                    print(expectedOut)
                    print(tup_result)
                    if (expectedOut == tup_result):
                        print("Success!")
                    else:
                        print("Fail!")
                #currently has a newline character at the end of each result except the first, which is an empty string
            #TODO: parse the results
        else:
            #TODO: preferentially run main.py or projectname.py before asking for help
            print("Could not run project in "+studentFolder.name)
            print(str(len(pythonFiles))+" python files in "+studentFolder.name+"/"+latestRevision.name)
            #TODO: add interface to specify which file is desired