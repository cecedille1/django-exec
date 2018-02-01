#!groovy

DEFAULT_BRANCH = 'master'
DEPLOYED_BRANCH = 'releases'

is_merge_request = env.gitlabTargetBranch != env.gitlabSourceBranch;
index_url = 'https://pi.emencia.net/jenkins/release';
index = 'emencia';

def get_code() {
    checkout scm
    if (env.gitlabSourceBranch == null) {
        checkout([
            $class: 'GitSCM',
            branches: [[name: "origin/${DEFAULT_BRANCH}"]],
        ])
    } else if (is_merge_request) {
        echo "Pre Build Merge ${env.gitlabTargetBranch} and ${env.gitlabSourceBranch}"
        checkout([
            $class: 'GitSCM',
            branches: [[name: "origin/${env.gitlabSourceBranch}"]],
            extensions: [
                [
                    $class: 'PreBuildMerge',
                    options: [
                        fastForwardMode: 'NO_FF', mergeRemote: 'origin', mergeStrategy: 'MergeCommand.Strategy',
                        mergeTarget: "${env.gitlabTargetBranch}"
                    ]
                ]
            ]
        ])
    } else {
        checkout([
            $class: 'GitSCM',
            branches: [[name: "origin/${env.gitlabSourceBranch}"]],
        ])
    }
}
def run_tests(python_version, django) {
    def django_major = django[0];
    def django_minor = django[1];
    def django_minor_next = django_minor + 1;

    def test_name = "python${python_version}-django${django_major}.${django_minor}";
    def venv_path = "${workspace}/.envs/${test_name}";

    pip('install', "'django>=${django_major}.${django_minor},<${django_major}.${django_minor_next}'", venv_path);
    venv("-r ${workspace}/requirements.txt -r ${workspace}/requirements.d/tests.txt",  venv_path, python_version);
/*
    if (python_version == '2') {
        pip('install', "-r ${workspace}/requirements.d/tests-python2.txt", venv_path);
    }
*/
    run('pytest',  "--junitxml=${workspace}/unit-${test_name}.tests.xml", venv_path);
}
def run(prog, command, env=default_env) {
    sh("${env}/bin/${prog} ${command}");
};

def pip(prog, command, env=default_env) {
    if (prog == 'install' && index_url) {
        command = "-i ${index_url} ${command}";
    }
    command = "${prog} ${command}";
    run('pip', command, env)
};
def setuppy(command, env=default_env) {
    run('python', "setup.py ${command}", env)
}

def venv(requirements, env=default_env, version=3) {
    if (!fileExists("${env}/bin/python")) {
        sh("virtualenv --python python${version} ${env}");
    }
    if (requirements) {
        pip('install', requirements, env);
    }
    return env;
}

def notify(text) {
    if (is_merge_request) {
        echo text
        addGitLabMRComment text
    }
}

notify "Building in ${env.BUILD_URL}"
node {
    workspace = pwd();
    default_env = "${workspace}/.envs/default";

    stage 'Checkout', {
        get_code()
    }
    gitlabBuilds(builds: [
            'Quality & tests setup',
            'Quality',
            'Tests',
    ]) {
        stage 'Quality & tests setup', {
            gitlabCommitStatus('Quality & tests setup') {
                venv('-r requirements.d/jenkins.txt');
            }
        }
        stage 'Quality', {
            gitlabCommitStatus('Quality') {
                writeFile(file: './flake8.log', text: '');
                try {
                    run('flake8', "--output-file=${workspace}/flake8.log");
                } finally {
                    step([
                            $class: 'WarningsPublisher',
                            defaultEncoding: 'UTF-8',
                            healthy: '20',
                            unHealthy: '100',
                            parserConfigurations: [[
                            parserName: 'Pep8',
                            pattern: "flake8.log"
                            ]]
                    ]);
                }
            }
        }
        stage 'Tests', {
            gitlabCommitStatus('Tests') {
                try {
                    parallel(
                            test_python2_django18: {run_tests('2', [1, 8])},
                            test_python2_django19: {run_tests('2', [1, 9])},
                            test_python2_django110: {run_tests('2', [1, 10])},
                            test_python2_django111: {run_tests('2', [1, 11])},
                            test_python3_django18: {run_tests('3', [1, 8])},
                            test_python3_django19: {run_tests('3', [1, 9])},
                            test_python3_django110: {run_tests('3', [1, 10])},
                            test_python3_django111: {run_tests('3', [1, 11])},
                            );
                } finally {
                    step([
                            $class: 'JUnitResultArchiver',
                            testResults: "*.tests.xml",
                    ]);
                }
            }
        }
        notify("Seems pretty good ${env.BUILD_URL}");
    }

    if (env.gitlabSourceBranch == DEPLOYED_BRANCH && env.gitlabActionType == 'PUSH' || env.gitlabSourceBranch == null) {
        gitlabBuilds(builds: [
                'Publish',
        ]) {
            stage 'Publish', {
                gitlabCommitStatus('Publish') {
                    setuppy("register -r ${index}");
                    setuppy("sdist bdist_wheel upload -r ${index}");
                }
            }
        }
    }
}
