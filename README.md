# AgroClima Monitor 2.0

Projeto acadêmico de monitoramento agrícola. O aplicativo em Python exibe umidade do solo e do ar, temperatura e luminosidade, registra leituras em SQLite e consulta previsões meteorológicas no Open-Meteo.

## Testar no Windows

1. Baixe o ZIP da [versão 2.0 para Windows x64](https://github.com/muryllo1110oliver/AgroClima/releases/tag/v2.0) e extraia todo o conteúdo em uma pasta onde você possa gravar arquivos.
2. Abra `AgroClimaMonitor.exe`. Mantenha a pasta `_internal` ao lado do executável. Essa versão já inclui o Python.
3. No aplicativo, abra **Configurações → Modo demonstração**. O painel e os gráficos serão preenchidos com leituras simuladas, sem precisar conectar o Arduino.

## Executar pelo código-fonte

No Windows, com Python 3.12 x64 instalado, extraia o código e execute `instalar.bat` seguido de `executar.bat`. Para abrir diretamente em demonstração, rode `executar.bat --demo`. No VS Code, abra a raiz do projeto e selecione a configuração **AgroClima — demonstração** depois de instalar as dependências. A instalação das dependências e a previsão meteorológica exigem internet.

## Conectar o Arduino

Abra [Codigo.ino](firmware/Codigo/Codigo.ino) na Arduino IDE. No Gerenciador de Bibliotecas, instale **DHT sensor library**, da Adafruit, e a dependência **Adafruit Unified Sensor**. Selecione a placa e a porta serial antes de gravar o sketch. A compilação foi verificada para o Arduino Uno.

O sketch usa um DHT11 no pino digital 2, um sensor de umidade do solo em A0 e um LDR em A1. Envia as leituras em JSON pela serial a 115200 baud, aproximadamente a cada 2 segundos. Feche o Monitor Serial da Arduino IDE e selecione a porta COM em **Configurações** no aplicativo.

O firmware fornecido cobre a leitura dos sensores. Os estados de bomba e sombreamento podem ser explorados no simulador. A placa e os sensores físicos exigem teste em bancada.

O aplicativo cria o banco SQLite durante o uso. A [nota da versão Windows](docs/ENTREGA_FINAL.md) registra a correção de HTTPS e os resultados da validação original.
