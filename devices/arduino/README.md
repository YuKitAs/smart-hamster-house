* Upload `*.ino` to Arduino

* Remove all weights on the scale and run (with `python3.8+`):

```console
$ python3 main.py &
```

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
/path/to/Projects/smart-hamster-house/devices/arduino/arduino.log {
  daily 
  rotate 7
  missingok
  compress
  copytruncate
}
```