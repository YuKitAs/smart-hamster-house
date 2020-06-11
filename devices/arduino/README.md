* Upload `*.ino` to Arduino

* Remove all weights on the scale and run:

```console
$ python3 main.py &
```

* Check logs (DB operations are logged at INFO level):

```console
$ tail -f logs/arduino.log
```

* Check database:

```console
$ influx
> USE water
> SELECT * FROM level
> USE weight
> SELECT * FROM weight [WHERE type='hamster']
```

* Log rotation config: `/etc/logrotate.d/arduino`