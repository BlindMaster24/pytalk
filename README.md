# Pytalk

py-talk is a simple but powerful pythonic library for making bots for the [TeamTalk5 Conferencing System](https://bearware.dk/)


### Installing

Python 3.11 or higher is required

#### From PyPI

```bash
pip install py-talk-ex
```

#### From source

```bash
git clone https://github.com/BlindMaster24/pytalk
cd pytalk
pip install pipx
pipx install hatch
hatch env create
```

### Development

To run development tasks like linting, formatting, and type checking, use `hatch run`:

```bash
hatch run dev:lint
hatch run dev:format
hatch run dev:typecheck
hatch run docs:build
hatch run sdk-download
```

### Usage

If you have a TeamTalk SDK license, you can pass it when instantiating the bot so
the SDK is initialized with your credentials. Both `license_name` and
`license_key` must be provided together; otherwise the library raises a
`ValueError`. The TeamTalk SDK license is process-wide, so all bot instances in
the same process must reuse the same credentials.

```python
import pytalk

bot = pytalk.TeamTalkBot(
    client_name="PyTalk",
    # Optional: apply your TeamTalk SDK license if you have one
    license_name="Your Company",
    license_key="XXXXX-XXXXX-XXXXX-XXXXX",
)

@bot.event
async def on_ready():
    test_server = pytalk.TeamTalkServerInfo({"host": "localhost", "tcp_port": 10335, "udp_port": 10335, "username": "user", "password": "pass"})
    await bot.add_server(test_server)

@bot.event
async def on_message(message):
    if message.content.lower() == "ping":
        message.reply("pong")

bot.run()
```


## Documentation

You can find the full documentation [here](http://pytalk.readthedocs.io/en/latest)



## Troubleshooting

#### Error when downloading the teamtalk sdk


```
Error: patoolib.util.PatoolError: could not find an executable program to extract format 7z; candidates are (7z,7za,7zr,unar),
```

Solution:

```
$ sudo apt install p7zip-full
```

Explanation:

The error is caused by the fact that the `patool` library requires a program to extract 7z files. The error message lists the programs it tried to use, and the solution is to install one of them. In this case, `p7zip-full` is a good choice.


## Contributing

So you want to contribute to teamtalk.py? Great! There are many ways to contribute to this project, and all contributions are welcome.
If you have found a bug, have a feature request or want to help improve documentation please [open an issue](https://github.com/BlindMaster24/pytalk/issues/new)_

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
