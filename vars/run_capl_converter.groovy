def call(String fileList, String conversionType) {
    def converterDir = "C:\\Temp\\code\\capl-converter"

    node('slave_agent') {
        stage("Running CAPL conversion") {
            def resultDir = currentBuild.projectName + '_test' + currentBuild.number

            dir(converterDir) {
                bat label: '', script: 'py -3 CAPLconversionMain.py --'+ conversionType + ' test' + currentBuild.number + ' ' + fileList + ' ' +  resultDir
            }
        }
    }
}