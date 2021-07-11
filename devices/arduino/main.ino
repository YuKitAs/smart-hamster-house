#include "HX711_ADC.h"
#include "DHT.h"
#include "LiquidCrystal_I2C.h"
#include "TimeLib.h"
#include <Wire.h>
#include <ArduinoJson.h>

#define DHTPIN 2 // D2 to DHT sensor
#define DHTTYPE DHT11
DHT dht(DHTPIN, DHTTYPE);

#define LIQUIDPIN 3 // D3 to liquid level sensor

HX711_ADC LoadCell(4, 5); // weighing sensor: D4 - DT, D5 - SCK

LiquidCrystal_I2C lcd(0x27, 16, 2); // LCD address

int liquidLevel = 0;
int loopCounter = 0;

const size_t capacity = JSON_OBJECT_SIZE(2);
DynamicJsonDocument doc(capacity);

void setup() {
  LoadCell.begin();
  LoadCell.start(2000); // wait for stabilization
  LoadCell.setCalFactor(376.0); // TODO: adjust the calibration factor with a known weight

  Serial.begin(9600);

  dht.begin();
  lcd.init();
  lcd.backlight();

  // TODO: set current datetime
  setTime(00,12,00,12,7,2021);
}

// read weight every 1s, liquid level every 5s, humidity & temperature every 60s
void loop() {
  if (loopCounter > 60) {
    loopCounter = 0;
  }

  if (loopCounter % 60 == 0) {
    lcd.clear();
    updateDateTime();
    readHumidityAndTemperature();
  }

  if (loopCounter % 5 == 0) {
    readLiquidLevel();
  }
  
  readWeight();
  loopCounter++;
  delay(1000);
}

boolean readLiquidLevel() {
  liquidLevel = digitalRead(LIQUIDPIN);
  serialPrint(liquidLevel <= 0, 0);
}

float readWeight() {
  LoadCell.update();
  float weight = LoadCell.getData(); // weight in gram
  if (weight > 0) {
    serialPrint(false, weight);
  }
}

void updateDateTime() {
  char datetime[14];
  sprintf(datetime, "%d:%d %d/%d/%d", hour(), minute(), day(), month(), year());
  lcd.setCursor(0,0);
  lcd.print(datetime);
}

void readHumidityAndTemperature() {
  int h = dht.readHumidity();
  int t = dht.readTemperature();

  lcd.setCursor(2,1);
  lcd.print("H:");
  lcd.print(h);
  lcd.print("% ");
  lcd.setCursor(8,1);
  lcd.print("T:");
  lcd.print(t);
  lcd.print("\xDF""C");
}

void serialPrint(bool alarm, float weight) {
  doc["liquid_alarm"] = alarm;
  doc["weight"] = weight;
  serializeJson(doc, Serial);
  Serial.println();
}
