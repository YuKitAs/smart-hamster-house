* Upload `*.ino` to Arduino

* Remove all weights on the scale, start Tmux session and run from the project root (with `python3.8+`):

```console
$ tmux
$ python3 devices/arduino/main.py &
```

Detach Tmux session with `Ctrl + b` and `d`.

Re-attach with `tmux attach-session -t 0`.

* Check logs:

```console
$ tail -f logs/arduino.log
$ grep INFO logs/arduino.log
```

* Check database:

```console
$ influx
> USE water
> SELECT * FROM level
> USE weight
> SELECT * FROM weight [WHERE type='hamster']
```

* Log rotation config `/etc/logrotate.d/arduino`:

```
/path/to/Projects/smart-hamster-house/logs/arduino.log {
  daily 
  rotate 7
  missingok
  compress
  copytruncate
}
```