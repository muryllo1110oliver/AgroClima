#include <DHT.h>

#define DHT_PIN 2
#define DHT_TYPE DHT11
#define SOLO_PIN A0
#define LDR_PIN A1

DHT dht(DHT_PIN, DHT_TYPE);

const int SOLO_SECO = 547;
const int SOLO_MOLHADO = 350;

const unsigned long INTERVALO_LEITURA = 2000;
unsigned long ultimaLeitura = 0;

void setup() {
  Serial.begin(115200);
  dht.begin();

  pinMode(SOLO_PIN, INPUT);
  pinMode(LDR_PIN, INPUT);

  delay(2000);
}

void loop() {
  if (millis() - ultimaLeitura < INTERVALO_LEITURA) {
    return;
  }

  ultimaLeitura = millis();

  int soloBruto = analogRead(SOLO_PIN);
  int luzBruta = analogRead(LDR_PIN);

  int umidadeSolo = map(
    soloBruto,
    SOLO_SECO,
    SOLO_MOLHADO,
    0,
    100
  );

  umidadeSolo = constrain(umidadeSolo, 0, 100);

  int luminosidade = map(
    luzBruta,
    0,
    1023,
    0,
    100
  );

  luminosidade = constrain(luminosidade, 0, 100);

  float temperatura = dht.readTemperature();
  float umidadeAr = dht.readHumidity();

  if (isnan(temperatura) || isnan(umidadeAr)) {
    return;
  }

  Serial.print("{");

  Serial.print("\"soil\":");
  Serial.print(umidadeSolo);

  Serial.print(",\"soil_raw\":");
  Serial.print(soloBruto);

  Serial.print(",\"air_temp\":");
  Serial.print(temperatura, 1);

  Serial.print(",\"air_humidity\":");
  Serial.print(umidadeAr, 1);

  Serial.print(",\"light\":");
  Serial.print(luminosidade);

  Serial.print(",\"light_raw\":");
  Serial.print(luzBruta);

  Serial.println("}");
}