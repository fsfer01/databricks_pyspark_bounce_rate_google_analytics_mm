# RESUMO:
Esse é um projeto desenvolvido e implantado por mim na MadeiraMadeira. Essa é uma ETL realizada no Databricks com PySpark modelando dados do Google Analytics direto de um bucket do S3. Após essa modelagem, criei um dashboard no looker para o time responsável.
![image](https://github.com/user-attachments/assets/3e8e9a0e-8db6-4c01-a5dd-93c16161e1d6)



## **Objetivo da Solução / KPI de Negócio:**
O objetivo do KPI bounce rate, conhecido também como taxa de rejeição é medir a porcentagem de visitantes que acessam uma página do site ou App e saem imediatamente, sem interagir com ela. Em outras palavras, é a porcentagem de visitantes que "rejeitam" a página. 

O objetivo é avaliar a qualidade do tráfego e do conteúdo do site, identificando possíveis problemas que possam estar afetando a experiência do usuário e levando ao abandono do site. Assim, o bounce rate é um indicador importante para auxiliar na otimização do site e na melhoria da experiência do usuário.


## **Perguntas e Respostas Simples:** 

O que é bounce rate?
R: O bounce rate é a taxa de rejeição do site, ou seja, a porcentagem de visitas em que a pessoa acessa uma única página e sai sem interagir com o restante do site.

Como o bounce rate é calculado?
R:O bounce rate é calculado dividindo o número de visitas que resultam em uma única visualização de página pelo número total de visitas.
    
O que um bounce rate alto significa?
R: Um bounce rate alto pode indicar que os visitantes do site não estão encontrando o que procuram, ou que a página de destino não está correspondendo às expectativas do usuário.
    
que um bounce rate baixo significa?
R: Um bounce rate baixo pode indicar que os visitantes estão interagindo com o site de forma mais profunda, visitando mais páginas ou consumindo mais conteúdo.
    
Como posso melhorar o bounce rate?
R: Existem várias maneiras de melhorar o bounce rate, como aprimorar o conteúdo do site, melhorar o design e a navegação, reduzir o tempo de carregamento das páginas e tornar as chamadas para ação mais claras e atraentes. Para isso, é recomendado entrar em contato com às pessoas abaixo:
    
-censurado@madeiramadeira.com.br
-censurado@madeiramadeira.com.br
-censurado@madeiramadeira.com.br

## **Regras de Negócio:**
Nessa solução de dados, foram criados alguns campos com métricas solicitadas pela área de negócio. Estamos considerando os dados que houve eventos de interação, através do filtro: where totals.visits = 1.

Segue Consulta SQL que simula os dados que estão nessa ETL. Essa Query deve ser utilizada no BigQuery.

~~~~sql
select
-- sessions (metric)
count(distinct concat(fullvisitorid, cast(visitstarttime as string))) as sessions,
-- bounces (metric)
count(distinct case when totals.bounces = 1 then concat(fullvisitorid, cast(visitstarttime as string)) else null end) as bounces,
-- bounce rate (metric)
count(distinct case when totals.bounces = 1 then concat(fullvisitorid, cast(visitstarttime as string)) else null end) / count(distinct concat(fullvisitorid, cast(visitstarttime as string))) as bounce_rate,
-- soft (metric)
count(distinct case when totals.pageviews = 1 then concat(fullvisitorid, cast(visitstarttime as string)) else null end) as soft,
-- soft bounce (metric)
count(distinct case when totals.pageviews = 1 then concat(fullvisitorid, cast(visitstarttime as string)) else null end) / count(distinct concat(fullvisitorid, cast(visitstarttime as string))) as soft_bounce
from `censurado_ga360.ga_sessions_202301*`
where totals.visits = 1
~~~~









