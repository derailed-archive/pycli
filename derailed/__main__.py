from typing import TypedDict
from msgspec import msgpack, json
import pathlib
import typer
from appdirs import user_data_dir
from sys import stderr
from rich.status import Status
import requests


app = typer.Typer(name='derailed')


class URLConfig(TypedDict):
    gateway: str
    api: str


class Config(TypedDict):
    token: str | None
    version: int | str | None
    urls: URLConfig


def grab_config() -> Config:
    path = user_data_dir('Derailed Python', 'Derailed')
    if not pathlib.Path(path).exists():
        raise typer.Abort('Directories not setup, please run `derailed setup` to setup')

    # TODO: validate integrity of config
    with open(path + '\\_config.mspk', 'rb') as file:
        return msgpack.decode(file.read(), type=dict)


def change_config(new_config: Config) -> None:
    path = user_data_dir('Derailed Python', 'Derailed')
    if not pathlib.Path(path).exists():
        raise typer.Abort('Directories not setup, please run `derailed setup` to setup')

    with open(path + '\\_config.mspk', 'wb') as f:
        f.write(msgpack.encode(new_config))


@app.command('setup')
def setup(api_url: str, gateway_url: str) -> None:
    with Status('Setting up directories...') as status:
        status.start()
        path = user_data_dir('Derailed Python', 'Derailed')
        pathlib.Path(path).mkdir(parents=True, exist_ok=True)
        status.stop()

    print('Finished setup of directories', file=stderr)


    with Status('Setting up configuration...') as status:
        status.start()
        config_dir = path + '/_config.mspk'

        with open(config_dir, 'wb') as f:
            f.write(msgpack.encode({
                'token': None,
                'version': 0,
                'urls': {
                    'gateway': gateway_url,
                    'api': api_url
                }
            }))

        status.stop()


    print('Finished setup of configuration file', file=stderr)


@app.command('_cfg_drop')
def cfg_drop() -> None:
    config = grab_config()
    print(config, file=stderr)


@app.command('register')
def register(username: str, email: str, password: str) -> None:
    config = grab_config()


    if config['token'] != None:
        raise typer.Abort('Already logged in, please run `derailed logout` to register a new user')


    r = requests.post(config['urls']['api'] + '/v1/register', data=json.encode({'username': username, 'email': email, 'password': password}))

    if not r.ok:
        print(r.text, file=stderr)
        raise typer.Abort('Invalid registration information')


    data = json.decode(r.text, type=dict)


    config['token'] = data.pop('token')


    change_config(config)


    print(f'Welcome to Derailed {data["username"]}!', file=stderr)


if __name__ == '__main__':
    app()
