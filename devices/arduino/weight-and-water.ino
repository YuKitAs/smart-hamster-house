#include "HX711_ADC.h"
#include <ArduinoJson.h>
#define liquidPin 3

HX711_ADC LoadCell(5, 6); // DT - D5, SCK - D6

int liquidLevel = 0;
int loopCount = 0;

const size_t capacity = JSON_OBJECT_SIZE(2);
DynamicJsonDocument doc(capacity);

void setup() {
  LoadCell.begin();
  LoadCell.start(2000); // wait for stabilization
  LoadCell.setCalFactor(376.0);

  Serial.begin(9600);
}

void loop() {
  if (loopCount < 5) {
    readWeight();
    loopCount++;
    delay(1000);
  } else {
    readLiquidLevel();
    loopCount = 0;
  }
}

void readLiquidLevel() {
  liquidLevel = digitalRead(liquidPin);
  serialPrint(liquidLevel <= 0, 0);
}

void readWeight() {
  LoadCell.update();
  float weight = LoadCell.getData(); // weight in gram
  if (weight > 0) {
    serialPrint(false, weight);
  }
}

void serialPrint(bool alarm, float weight) {
    doc["liquid_alarm"] = alarm;
    doc["weight"] = weight;
    serializeJson(doc, Serial);
    Serial.println();
}
