# AgroClima Monitor 2.0

Projeto acadêmico de monitoramento agrícola. O aplicativo em Python exibe umidade do solo e do ar, temperatura e luminosidade, registra leituras em SQLite e consulta previsões meteorológicas no Open-Meteo.

## Testar no Windows

1. Baixe o código do repositório e extraia os arquivos.
2. Com Python 3.12 x64 instalado, execute `instalar.bat` e depois `executar.bat`.
3. Use o modo de demonstração para conhecer o aplicativo sem conectar o Arduino. A instalação das dependências e a previsão meteorológica exigem internet.

## Conectar o Arduino

Abra [Codigo.ino](firmware/Codigo/Codigo.ino) na Arduino IDE, instale a biblioteca DHT e carregue o sketch. O código usa um DHT11 no pino digital 2, um sensor de umidade do solo em A0 e um LDR em A1. Envia as leituras em JSON pela serial a 115200 baud, aproximadamente a cada 2 segundos. Feche o Monitor Serial da Arduino IDE e selecione a porta COM no aplicativo.

O sketch fornecido envia leituras dos sensores. O banco e os logs são criados pelo aplicativo durante o uso.

A [nota da versão Windows](docs/ENTREGA_FINAL.md) descreve a correção de HTTPS e os testes registrados na entrega original.
