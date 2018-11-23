import com.cloudbees.ops.Builder;

pipeline {

    agent none

    options {
        buildDiscarder(logRotator(numToKeepStr:'30'))
        timeout(time: 30, unit: 'MINUTES')
        skipStagesAfterUnstable()
        timestamps()
        disableConcurrentBuilds()
    }

    stages {

        stage('Build') {
          agent {
            label "docker"
          }
          steps {
            script {
              def builder = new Builder()
              builder.scmUrl      = 'ssh://git@github.com/cloudbees/webhook-to-websocket.git'
              builder.dockerImage = "cloudbees/cloudbees-hooksocket"
              builder.orchestrate()
            }
          }
        }

    }
}
