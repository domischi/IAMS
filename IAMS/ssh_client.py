## Handles the connection to the cluster
import paramiko     #Provides SSH functionality
import os           #Used to setup the Paramiko log file
import logging      #Used to setup the Paramiko log file
import socket       #This method requires that we create our own socket

## From https://stackoverflow.com/questions/53761170/ssh-with-2fa-in-python-using-paramiko
class SSHClient(paramiko.SSHClient):
    duo_auth = True

    def handler(self, title, instructions, prompt_list):
        answers = []
        for prompt_, _ in prompt_list:
            prompt = prompt_.strip().lower()
            if prompt.startswith('password'):
                answers.append(self.password)
            elif prompt.startswith('verification'):
                answers.append(self.totp)
            elif prompt.startswith('duo two-factor login for'):
                answers.append(self.totp)
            else:
                raise ValueError('Unknown prompt: {}'.format(prompt_))
        return answers

    def auth_interactive(self, username, handler):
        if not self.totp:
            raise ValueError('Need a verification code for 2fa.')
        self._transport.auth_interactive(username, handler)

    def _auth(self, username, password, pkey, *args):
        self.password = password
        saved_exception = None
        two_factor = False
        allowed_types = set()
        two_factor_types = {'keyboard-interactive', 'password', 'publickey'}

        if self.duo_auth or two_factor:
            logging.info('Trying 2fa interactive auth')
            return self.auth_interactive(username, self.handler)

        if password is not None:
            logging.info('Trying password authentication')
            try:
                self._transport.auth_password(username, password)
                return
            except paramiko.SSHException as e:
                saved_exception = e
                allowed_types = set(getattr(e, 'allowed_types', []))
                two_factor = allowed_types & two_factor_types

        assert saved_exception is not None
        raise saved_exception

def upload_directory(local_path, remote_path, client):
    local_tar = "upload.tar.gz"
    remote_tar = "/tmp/upload.tar.gz"
    logging.info(f'Upload {local_path} to remote {remote_path}')

    os.system(f"""tar czf {local_tar} {local_path}""")

    sftp = client.open_sftp()
    sftp.put(local_tar, remote_tar)
    sftp.close()
    cmds = [
            f'tar xf {remote_tar} -C {remote_path}',
            f'rm {remote_tar}',
            ]
    for cmd in cmds:
        stdin, stdout, stderr = client.exec_command(cmd)
        output = stdout.readlines()
        logging.info('> '+cmd)
        logging.info(''.join(output))
        logging.info('\n')
    os.system(f"""rm {local_tar}""")

def create_scratch_link(client):
    general_scratch_place = "/scratch/"
    home_directory_link = 'scratch'
    _, stdout, _ = client.exec_command('ls ~')
    if not home_directory_link in ''.join(stdout.readlines()):
        print('Scratch has to be generated...', end='')
        client.exec_command(f'mkdir -p {general_scratch_place}/$USER')
        client.exec_command(f'ln -s {general_scratch_place}/$USER ~/{home_directory_link}')
        print('Done.')
    return f'~/{home_directory_link}'
