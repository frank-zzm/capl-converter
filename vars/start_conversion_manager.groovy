def call(String listFilePath, String numFiles, String conversionType, String isUrgent) {
    def fileLists = []
    def splitListDir
    stage ("Splitting input file") {
        node ('master') {
             try {
                echo "Path: $listFilePath"
                // Following variables are temporary solution for prototype and should be changed in future
                def script = "\\\\SE03-FS01.corp.int\\COMMON\$\\SE03\\DataLake\\Vision_tmp_data\\GVP-11882\\splitInputFile.py"
                def outputDir = "\\\\SE03-FS01.corp.int\\COMMON\$\\SE03\\DataLake\\Vision_tmp_data\\GVP-11882\\OutputData" + "\\${env.BUILD_NUMBER}\\"

                bat label: '', script: "py $script -n $numFiles -i $listFilePath -o $outputDir\\"

                splitListDir = new File(outputDir)
                fileLists = splitListDir.listFiles()
                                        .findAll { it.name ==~ '.*_Part[0-9]*.txt' }
            }
            catch (err) {
                echo "Error message" + err
                currentBuild.result = "FAILIURE"
            }
        }
    }

    def results = [:]
    stage("Start CAPL conversion sub-jobs") {
        def jobTitle
        if (isUrgent == 'true') {
            jobTitle = 'CAPLConversionHigh-Subjob'
        }
        else {
            jobTitle = 'CAPLConversion-Subjob'
        }

        def builders = [:]
        fileLists.eachWithIndex {
            list, id ->
            // Create a map to pass into the 'parallel' step so we can fire all the builds at once
            builders[id] = {
                    echo "Creating a new job: " + jobTitle + " for list " + list.getAbsolutePath()
                    def childJob
                    childJob = build (job: jobTitle,
                        parameters: [string(name: 'fileList', value: list.getAbsolutePath()), string(name: 'conversionType', value: conversionType)],
                        wait: true, propagate: false)
                    def childJobName = jobTitle + id
                    results.put(childJobName, childJob.result)
            }
        }
        parallel builders
    }

    stage("Analyzing results"){
        echo 'Job Status Summary:'
        results.each{ k, v -> echo 'Name:' + k + ' result: ' + v }

        // Delete folder created for splitting files
        splitListDir.deleteDir()
    }
}