import sys
import getopt
import os

inputCopyFile = "input.txt"

def main(argv):
    inputFile = ''
    outputDir = ''
    subFileSize = 0
    baseName = ''

    try:
        (opts, args) = getopt.getopt(argv, 'n:i:o:', ['numfiles=', 'ifile=', 'ofile='])
    except getopt.GetoptError:
        print ('Usage: ', sys.argv[0], '-n <numFiles> -i <inputFile> -o <outputDir>')
        sys.exit(2)
    for (opt, arg) in opts:
        if opt in ('-n'):
            subFileSize = int(arg)
        elif opt in ('-o'):
            outputDir = arg
        elif opt in ('-i'):
            inputFile = arg

    if not os.path.isdir(outputDir):
        os.mkdir(outputDir)

    baseName =  os.path.basename(inputFile)
    baseName =  os.path.splitext(baseName)[0]
    outputDir = os.path.join(outputDir, baseName)

    # Create new file which contains the same content as inputFile without empty lines and comments
    lines = open(inputFile, "r").readlines()
    clean_lines = []
    for line in lines:
        if not line.isspace() and line.strip()[0] != '#':
            clean_lines.append(line)
    clean_lines[-1] = clean_lines[-1].strip('\n')
    with open(inputCopyFile, "w+") as inFile:
        inFile.writelines(clean_lines)
        inFile.seek(0, 0)
        # Split the input file into multiple output files of size that is subFileSize
        # (while taking into account that the sequences are not interrupted)
        # Obtained output files should be saved in the outputDir
        split(inFile, outputDir, subFileSize)

    os.remove(inputCopyFile)

numberOfFiles = 0
# Create new output file in the outDir directory
def openNewOutputFile(outDir):
    global numberOfFiles
    fileName = outDir + '_Part' + str(numberOfFiles) + '.txt'
    of = open(fileName, 'a')
    numberOfFiles = numberOfFiles + 1
    return of

# Determine wheather the line starts with the plus sign
def lineStartsWithPlus(line):
    value = (True if line[0] == '+' else False)
    return value

# Determine the current sequence length
# Sequence is a set of files that should not be split when processing
def getSequenceLength(targetLineIndex):
    file = open(inputCopyFile, "r")
    sequenceLength = 1
    for (inx, line) in enumerate(file):
        if inx >= targetLineIndex:
            if lineStartsWithPlus(line):
                sequenceLength = sequenceLength + 1
            else:
                break
    file.close()
    return sequenceLength


def split(inFile, outDir, subFileSize):
    # Number of lines in current open file
    addedLines = 0
    isSequence = False

    of = openNewOutputFile(outDir)
    previousLine = inFile.readline()
    for (inx, line) in enumerate(inFile):
        if isSequence:
            of.write(previousLine)
            addedLines = addedLines + 1
            if not lineStartsWithPlus(line):
                isSequence = False
        elif lineStartsWithPlus(line):
            # One sequence is a line followed by a single or multiple lines that starts with plus sigh
            isSequence = True
            length = getSequenceLength(inx + 1)
            if addedLines + length < 1.3 * subFileSize:
                of.write(previousLine)
                addedLines = addedLines + 1
            else:
                of.close()
                of = openNewOutputFile(outDir)
                of.write(previousLine)
                addedLines = 1
        else:
            if addedLines < subFileSize:
                of.write(previousLine)
                addedLines = addedLines + 1
            else:
                of.close()
                of = openNewOutputFile(outDir)
                of.write(previousLine)
                addedLines = 1
        previousLine = line

    of.write(previousLine)
    of.close()


if __name__ == '__main__':
    main(sys.argv[1:])
