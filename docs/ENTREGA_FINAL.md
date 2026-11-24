# AgroClima Monitor 2.0 — correção meteorológica Windows

Validação realizada em 21/11/2026, Windows x64.

## Causa raiz comprovada

O erro foi reproduzido na interface do executável anterior. O Python utilizado para compilá-lo possui uma política SSL adicional: SSLContext.__new__ carrega codex-rejected-cas.pem ao lado de ssl.py. Esse arquivo não estava incluído no pacote PyInstaller. A exceção surgia antes de abrir a conexão HTTP:

    urllib.request.urlopen → build_opener → HTTPSHandler
    http.client._create_https_context → ssl.create_default_context
    ssl.SSLContext.__new__ → load_verify_locations
    FileNotFoundError: [Errno 2] No such file or directory

Um executável mínimo, criado com o mesmo ambiente de compilação, reproduziu esse traceback. A inclusão do arquivo em _internal fez a mesma consulta HTTPS funcionar. Portanto, a correção trata a dependência ausente, além de melhorar as mensagens. Trocar apenas urllib por requests/certifi não resolveria essa particularidade do runtime.

## Correção

- Transporte com requests.Session, trust_env=False, timeout explícito de conexão e leitura de 12 segundos, raise_for_status() e certifi.where().
- Certificados incluídos em _internal/certifi/cacert.pem e política SSL do runtime em _internal/codex-rejected-cas.pem. O spec detecta essa dependência quando existe no Python de compilação; Python padrão também é suportado.
- Validação TLS permanece ativa. Nenhuma chamada a curl, PowerShell ou Python externo.
- Mensagens distintas para conexão, DNS, timeout, SSL, falha HTTP, JSON inválido, cidade não encontrada e distribuição incompleta.
- Open-Meteo Best Match explícito, preservando geocodificação, cidade, estado, país, precipitação em 24 horas, máxima probabilidade horária, temperatura, umidade, próxima chuva, atualização automática e manual.
- Consultas continuam nos workers existentes. A sessão HTTP é encerrada somente após os trabalhos pendentes terminarem, ao fechar o aplicativo.

## Testes

**124 passed in 25.54s**, sem testes ignorados na execução final.

Inclui geocodificação válida, cidade inexistente, estado incorreto, previsão válida, ausência de internet, DNS, timeout, SSL, HTTP 400/429/500/503, JSON inválido, certificado ausente, independência de variáveis externas de CA/proxy, precipitação/probabilidade, temperatura/umidade/próxima chuva, regressões da interface e teste real de HTTPS dentro do executável distribuído.

O teste automatizado iniciou AgroClimaMonitor.exe --weather-check com PATH restrito a Windows/System32, sem variáveis Python/Qt/virtualenv e com variáveis de certificado apontando deliberadamente para arquivos inexistentes. Resultado: frozen=true, certificate_in_bundle=true, external_python_on_path=null, três previsões reais e código de saída zero.

Também foi aberto o executável normalmente, com o mesmo ambiente isolado. Em Configurações, estado São Paulo e país BR, o botão **Buscar cidade e atualizar previsão** produziu os seguintes resultados reais:

| Cidade | Precipitação 24 h | Probabilidade máx. | Temperatura | Horário da consulta |
|---|---:|---:|---|---|
| Santos | 2,6 mm | 71% | 24,3–28,4 °C | 19:35:29 |
| Pedro de Toledo | 6,5 mm | 84% | 23,8–34,5 °C | 19:35:48 |
| São Paulo | 3,7 mm | 82% | 20,3–30,2 °C | 19:36:09 |

Esses valores registram o teste; novas consultas podem apresentar outras previsões. Dashboard e Gráficos também foram abertos na versão empacotada.

Atualização automática confirmada no executável: sem novo clique, o horário mudou de 19:36:09 para 19:41:10, após cinco minutos, mantendo a previsão válida de São Paulo. O teste usou o intervalo mínimo permitido pela interface (5 minutos); a distribuição entregue mantém o padrão de 30 minutos.

O executável inclui o runtime Python e não precisa de instalação externa de Python. A verificação foi feita neste Windows com Python externo indisponível no PATH; não foi utilizada uma segunda máquina com Python fisicamente desinstalado.

## Arquivos modificados

- agroclima/services/weather_service.py: transporte HTTPS e mensagens.
- agroclima/main_window.py: fechamento da sessão meteorológica após os workers.
- AgroClimaMonitor.spec: certificados e política SSL no bundle.
- requirements.txt: requests e certifi.
- requirements-build.lock.txt: versões exatas do ambiente compilado.
- main.py: opção de diagnóstico meteorológico do próprio executável.
- agroclima/services/weather_diagnostics.py (novo): consultas de validação.
- tests/test_weather_service.py e tests/test_review_regressions.py: mocks adaptados para Session e verificação dos campos da previsão.
- tests/test_weather_transport.py (novo): falhas e configuração HTTPS.
- tests/test_weather_packaged.py (novo): execução real sem Python externo.
- README.md e ENTREGA_FINAL.md: instruções e evidências desta entrega.

Serial, protocolo JSON do Arduino, SQLite, sensores, cálculos de desvio padrão e filtros dos gráficos não foram modificados. Configuração e banco da fonte foram preservados. Os testes de interface utilizaram uma cópia separada da distribuição.

## Dependências adicionadas

Diretas: requests==2.34.2, certifi==2026.11.20.
Transitivas: urllib3==2.8.0, charset-normalizer==3.5.2, idna==3.20.
Build validado com Python 3.12.14, PyInstaller 6.22.3 e PySide6 Essentials 6.12.0.

## Entrega e uso

- AgroClimaMonitor_2.0_Windows_Corrigido.zip: aplicativo pronto Windows x64.
- AgroClimaMonitor_2.0_Codigo_Completo.zip: fonte integral, testes, firmware, configuração, banco e instruções de build.
- SHA256_METEOROLOGIA.txt: hashes dos dois ZIPs.

Extraia o ZIP inteiro e abra AgroClimaMonitor.exe. Mantenha _internal ao lado do executável. Para atualizar uma instalação em uso, preserve seus arquivos config.json e data/agroclima.db.


