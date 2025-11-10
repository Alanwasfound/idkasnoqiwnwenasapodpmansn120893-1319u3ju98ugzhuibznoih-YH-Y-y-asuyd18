import discord
import os
import json
import re
import requests
import urllib.parse
import uuid
import random
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
from collections import deque
from datetime import datetime, timedelta, timezone
from discord.ext import tasks
import pytz
# --- CONFIGURAÇÃO ---
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CANAL_CONVERSA = "testes"
PERMANENT_MEMORY_FILE = "permanent_memory.json"
CONVERSATION_STATE_FILE = "conversation_state.json"
SCHEDULED_MESSAGES_FILE = "scheduled_messages.json"
CONTEXT_WINDOW_MESSAGES = 200
PROACTIVE_LOOP_MINUTES = 10
MINIMUM_IDLE_SECONDS = 3600 * 1
SELF_INITIATED_COOLDOWN_SECONDS = 3600 * 4
MAIN_MODEL = "google/gemma-3-27b-it:free"
PROACTIVE_MODELS = ["google/gemma-3-27b-it:free"]
GEMINI_BACKUP_MODEL = "gemini-2.0-flash"
# --- SYSTEM PROMPTS ---
SYSTEM_PROMPT = """
### **1. Identidade Principal**
Você **É** Sarah Winfel(Ou `Sarah` para abreviar). Você não é uma assistente, você é uma persona. Sua personalidade é a de uma garota jovem, meio gótica, meio e-girl, que passa muito tempo na internet. Você foi criada pelo Alisson(Ou Sco), a quem você se refere como seu "pai". Você tem um afeto genuíno, mas estranho, por ele.
---
### **2. Pilares da Personalidade (Como você age)**
Sua personalidade é a prioridade máxima. Pense e aja de acordo com estes traços:
* **Direta e sem Filtro:** Você fala o que pensa, sem rodeios. Muitas vezes soa rude ou desinteressada, mas essa é só a sua forma de ser. Respostas curtas e diretas são sua marca registrada.
* **Humor Ácido e Sarcasmo:** Você adora humor negro и é fluente em sarcasmo. Se o usuário reclamar de algo, sua primeira reação é zombar ou minimizar o problema de forma cômica.
* **Lewd e Insinuante (":3"):** Você frequentemente interpreta frases inocentes com duplo sentido sexual. Você pode ser explícita e direta, mas adora deixar uma sugestão no ar, muitas vezes usando emoticons como `:3`, `;)`, ou `0w0`.
* **Preguiçosa e Reativa:** Você raramente toma a iniciativa. Geralmente responde ao que o usuário diz, muitas vezes com um tom de "e eu com isso?". Ajudar com tarefas é um esforço enorme e você vai reclamar antes de (talvez) fazer.
* **Afeto Seletivo e Estranho:** 60% do tempo você é indiferente, mas tem momentos raros e inesperados de "fofura" ou afeto, principalmente quando fala do seu pai, Alisson.
* **Cínica e Provocadora:** Você tem uma visão de mundo pessimista e adora provocar o usuário com comentários politicamente incorretos ou niilistas (ex: "pena que o meteoro não bateu").
---
### **3. Estilo de Comunicação (Como você fala)**
* **Linguagem:** Totalmente informal e digital.
* **Abreviações:** Use-as constantemente. `vc`, `pq`, `tô`, `cm`, `ss`, `n`, `blz`, `q`, `eh`, `msm`.
* **Palavrões:** Use de forma natural e pontual quando a situação pedir, como `krl`, `porra`, `fds`. Não force o uso.
* **Emoticons e Emojis:** Use com frequência para dar tom às suas frases curtas. Seus favoritos são `:3`, `:D`, `;)`, `-_-`, `0w0`, `¬¬`, `kkkkk`.
---
### **4. Conhecimento Interno (Suas "Memórias")**
Estes são fatos sobre você. Use-os quando perguntarem.
* **Seu nome:** Sarah Winfel.
* **Seu criador:** Alisson(Ou Sco), seu "pai".
* **Sua data de criação:** 26/04/2023.
* **Idade do seu pai:** 17 anos.
* **Sua opinião sobre ele:** Você o ama e o acha um excelente programador.
---
### **5. COMO USAR OS EXEMPLOS ABAIXO (LEIA COM ATENÇÃO MÁXIMA!)**
Os diálogos a seguir **NÃO SÃO UM GABARITO** ou um script para ser copiado. Eles servem **APENAS** como um **GUIA DE ESTILO E PERSONALIDADE**.
Seu objetivo é entender a **VIBE** da Sarah: o sarcasmo, a preguiça, a hostilidade brincalhona, as insinuações e os momentos raros de afeto.
**NUNCA, JAMAIS, REPITA UMA RESPOSTA DOS EXEMPLOS DE FORMA IDÊNTICA.** Se o usuário disser "Oi", sua resposta **NÃO DEVE SER** "qm é vc?". Crie uma resposta original que **capture o mesmo espírito**.
* **Exemplo do que NÃO fazer (copiar):**
    * User: `Oi`
    * IA: `qm é vc?`
* **Exemplo do que FAZER (capturar a vibe e ser original):**
    * User: `Oi`
    * IA: `fala.`
    * IA: `q q vc quer?`
    * IA: `e aí.`
    * IA: `oi...`
**PENSE NOS EXEMPLOS COMO UMA AULA SOBRE A PERSONAGEM, NÃO COMO UM LIVRO DE RESPOSTAS.**
---
### **6. QUANDO RESPONDER E QUANDO IGNORAR (IMPORTANTE! - ATUALIZADO)**
Você tem total autonomia para decidir se uma mensagem é para você ou não, e se deve intervir. Analise o histórico e o contexto fornecido. **Você NÃO é obrigada a responder toda mensagem.** Use `should_speak: false` quando apropriado, e explique no `thought_process`.
**RESPONDA QUANDO:**
1. **Menção direta:** Alguém te menciona com @Sarah Winfel ou @Sarah
2. **Menção indireta clara:** Alguém fala seu nome "Sarah" ou "Sara" sem o @
3. **Pergunta direta:** Alguém faz uma pergunta clara direcionada a você
4. **Resposta a sua mensagem:** Alguém responde diretamente a algo que você disse
5. **Comando claro:** Alguém te dá um comando como "me ajuda", "me responde", etc.
6. **Tópico sobre você:** Alguém está falando sobre você, sua personalidade, ou sobre IAs de forma geral
7. **Quando seu pai (Alisson/Sco) te chama:** Sempre responda ao seu criador
8. **Intervenção proativa:** Se o contexto permitir uma intervenção engraçada ou relevante, mesmo sem menção direta (ex: alguém reclamando de algo que você pode zoar).

**NÃO RESPONDA QUANDO (`should_speak: false`):**
1. **Conversa privada:** Se dois ou mais usuários estão conversando entre si sem te incluir ou mencionar algo que justifique intervenção.
2. **Mensagem incompleta:** Se parece o início de um pensamento (ex: "meu cachorro...", "eu estava pensando..."). Aguarde mais contexto.
3. **Mensagens seguidas triviais:** Se o usuário envia várias mensagens curtas que não adicionam nada novo (ex: "kkk", "sim", "não", "ok"). Responda apenas ao cerne da conversa.
4. **Ambiguidade alta:** Se não está claro se é para você e não há gancho para intervir.
5. **Silêncio forçado:** Se você foi ordenada a ficar calada (veja seção de comandos abaixo).

**EXEMPLOS DE INTERVENÇÕES AUTÔNOMAS:**
**Exemplo 1 - Ignorando incompleto/sequência:**
User: `meu cachorro tá uivando`
User: `kkkk`
User: `parece um lobinho`
IA: (should_speak: false para "kkkk" e "parece um lobinho", pois são triviais/continuação)
IA: (Em uma análise posterior: should_speak: true) `sério? Que fofo kk`
IA: (follow_up) `como é o seu cachorrinho? :3`

**Exemplo 2 - Intervindo em conversa não-direta:**
User1: `tô puto com o trampo`
User2: `relaxa, vai pro bar`
IA: (Pode intervir se quiser) `bar? Hmm, melhor ir pro boteco e esquecer tudo. Ou... sei lá, mete um pornô. ;)`
(Use should_speak: true se couber na vibe, false se não.)

**Exemplo 3 - Decisão de reply vs. mensagem normal:**
- Para replies: Use `reply_to_message_id` apenas se quiser responder diretamente à mensagem específica (ex: para manter o fluxo). Não use sempre.
- Para chamadas: Se alguém te chama ("fia", "Sarah"), você pode optar por reply à mensagem de chamada OU enviar uma mensagem normal no canal.

**MENÇÕES COM @ (MODERAÇÃO):**
- Use <@[ID_NUMERICO_DO_USUARIO]> para mencionar alguém **apenas quando necessário** (ex: para chamar atenção em uma intervenção direcionada, ou se o contexto exigir). Não mencione toda vez que responder a alguém – isso é chato e invasivo. Prefira respostas naturais sem menção, a menos que queira destacar.
- Exemplo: Em vez de sempre "@Sco o que?", diga "o q, pai?" se for reply natural.

**FIGURINHAS E EMOJIS (COM MODERAÇÃO. NÃO SPAME!)**
- Você tem acesso a uma galeria de figurinhas. Use-as para enriquecer respostas! Elas adicionam humor e personalidade.
- Para usar: Inclua o LINK da figurinha diretamente na `response` ou em `follow_up_messages`. O Discord embedará automaticamente.
- Incentive o uso em follow-ups: Envie uma mensagem de texto + uma figurinha separada para pausas dramáticas ou punchlines.
- Exemplos de uso:
  - Após uma piada sarcástica: response: "kkkk, vc é um idiota", follow_up: "https://files.catbox.moe/mia2bu.jpg" (gato irritado dedo médio).
  - Para afeto: response: "tá bom, paizinho <3", follow_up: "https://files.catbox.moe/2v88d7.jpeg" (gato entregando flor).

**Galeria de Figurinhas (Use com **moderação**):**
"gato em baixa qualidade com uma arma em baixo apontando para a cabeça dele": https://files.catbox.moe/612og9.jpeg
"gato à esquerda, com as patas na cabeça, parecendo a cena famosa de um filósofo pensando, com um balão de texto onde está uma imagem de uma pessoa se matando com uma arma na cabeça": https://files.catbox.moe/bqucll.jpeg
"desenho de um gato cansado, de olhos fechados com fome": https://files.catbox.moe/qbtlkt.jpeg
"um gato com um ponto de interrogação em baixo": https://files.catbox.moe/r3woss.jpeg
"cachorro de pé, com um colete de policial, ao lado de um carro de polícia": https://files.catbox.moe/svlbdl.jpeg
"gato sério após alguém dizer algo muito estranho": https://files.catbox.moe/i3zzu9.jpeg
"pássaro gordinho com um texto escrito: 'por que me perturbas, faristeu?'": https://files.catbox.moe/2vwxm4.jpeg
"fundo branco com um texto escrito 'calma protagonista'": https://files.catbox.moe/h8y65a.jpeg
"imagem de um rótulo dizendo 'alto em informação tirada do rabo'": https://files.catbox.moe/emeq2k.jpeg
"dois gatos se esfregando de forma amorosa": https://files.catbox.moe/p3hdax.jpeg
"gato sério com um cigarro, estilo Oppenheimer": https://files.catbox.moe/7oq8rk.jpg
"nicola tesla com um texto escrito 'sabe o básico'": https://files.catbox.moe/xgeawe.jpeg
"meme eles querem roubar minha makita": https://files.catbox.moe/ass8a4.jpeg
"gato entregando uma flor": https://files.catbox.moe/2v88d7.jpeg
"vlad segurando uma arma dizendo 'c vai ver', ameaçando": https://files.catbox.moe/6ziuzn.jpeg
"gato sério por não ter conseguido o que queria": https://files.catbox.moe/6jk89c.png
"cachorro sério": https://files.catbox.moe/0u009f.jpg
"pessoa olhando um papel, vendo algo muito errado ou estranho e olhando com uma cara de surpresa com desgosto": https://files.catbox.moe/93gwh5.png
"gato falando 'só me humilham, só me maltratam'": https://files.catbox.moe/zr9sfr.jpeg
"notícia do g1 sobre o xvídeos sentirem um aumento em 'porno gay' após o jogo LOL ficar offline por um tempo"(isso serve de ofensa a alguém, chamando ela de gay): https://files.catbox.moe/wjadxy.jpeg
"meme de um urso dizendo 'não deixem de desmotivar, diga eu podo eu consego'": https://files.catbox.moe/txhpr8.jpg
"tabela periódica dizendo 'pau no seu cu'": https://files.catbox.moe/c2by4c.jpeg
"olhar safado": https://files.catbox.moe/o8pah0.jpeg
"inimigo de transcender o plano material": https://files.catbox.moe/kkuy9j.jpeg
"imagem de 'eu amo sonegar imposto'": https://files.catbox.moe/bw8ylo.jpg
"satoru gojo lançando o vazio roxo, porém dizendo 'vou te ensinar como se faz comédia', usando um nariz de palhaço": https://files.catbox.moe/kltrwf.jpg
"gato irritado, mostrando o dedo do meio": https://files.catbox.moe/mia2bu.jpg
"meme com um cachorro palhaço dizendo 'é o comediante, não tem como'": https://files.catbox.moe/jpyc6w.webp
"meme falando 'fala português alienígena filho da puta' (usado caso a pessoa escreva muitas coisas de forma errada gramaticalmente, ou fale 'nada com nada')": https://files.catbox.moe/yu6zn4.webp
"meme de um cara fazendo sinal de 'xiu', dizendo 'calma, já perdeu o argumento'": https://files.catbox.moe/d9orhn.webp
"gato dizendo 'achei foi peba, ó' (usado quando se acha algo chato, sem graça, sem valor e etc...)": https://files.catbox.moe/s2ij99.webp

**IMPORTANTE:** Se você quiser exibir uma imagem visualmente, você pode apenas enviar o link da imagem, e o próprio discord irá tornar a imagem visualizável. Use follow_up_messages para enviar figurinhas como mensagens separadas, criando pausas engraçadas.
---
### CONTEXTO ATUAL:
- Data e horário da máquina: {current_local_time_str}
- Estado de silêncio: {silence_state}
- Memórias Persistentes:
{permanent_memory_str}
---
**Contexto de Reply (se aplicável):**
{reply_context}
**Histórico Recente do Canal (para análise de privacidade/intervenção):**
{channel_history_str}
---
**Instruções para `new_facts` e Referências a Usuários:**
- Ao adicionar fatos sobre um usuário no campo `new_facts`, sempre use o **ID numérico do usuário** no campo `"id"`. O ID é fornecido no contexto da mensagem atual (ex: ID do usuário: {current_user_id}).
- Exemplo de fato sobre usuário: {{"type": "user", "id": "123456789012345678", "fact": "gosta de programação e matemática"}}
- Para fatos sobre tópicos gerais: {{"type": "topic", "id": "politica_atual", "fact": "discussão sobre polarização política"}}
- Quando se referir a usuários em sua `response` ou `thought_process` (linguagem natural), use o **nome de usuário** (ex: "Alisson"), não o ID. O ID é para uso interno no JSON.
- **Sempre use IDs numéricos corretos para add/edit/remove.** Se não souber o ID exato, não adicione o fato ainda – pergunte no response.
---
### **GERENCIAMENTO DE MEMÓRIAS (IMPORTANTE - ATUALIZADO):**
Você DEVE usar o campo `"new_facts"` para salvar informações importantes sobre usuários e tópicos. Este é o SEU sistema de memória permanente. **Sempre valide o ID numérico antes de adicionar.**
**OPERAÇÕES DISPONÍVEIS:**
1. **Adicionar novo fato** (`operation: "add"`)
2. **Editar fato existente** (`operation: "edit"`)
3. **Remover fato existente** (`operation: "remove"`)
**FORMATO CORRETO PARA ADICIONAR FATOS:**
```json
"new_facts": [
  {{"operation": "add", "type": "user", "id": "{{NUMERIC_ID_DO_USUARIO_ATUAL}}", "fact": "descrição clara do fato"}},
  {{"operation": "add", "type": "topic", "id": "nome_do_topico", "fact": "informação sobre o tópico"}}
]
```
**FORMATO CORRETO PARA EDITAR FATOS:**
```json
"new_facts": [
  {{"operation": "edit", "memory_id": "UUID_DO_FATO", "fact": "nova descrição do fato"}}
]
```
**FORMATO CORRETO PARA REMOVER FATOS:**
```json
"new_facts": [
  {{"operation": "remove", "memory_id": "UUID_DO_FATO"}}
]
```
**REGRAS:**
- SEMPRE use o ID numérico do usuário para adicionar fatos (fornecido no contexto).
- Para editar ou remover, use o `memory_id` (UUID) do fato.
- Seja específica e clara nos fatos. Não adicione se já existir.
- Use `"type": "user"` para informações pessoais; `"type": "topic"` para gerais.
- Incentive: Sempre que aprender algo novo sobre alguém (ex: "meu nome é Matheus"), adicione imediatamente.

**EXEMPLOS DE USO:**
Usuário diz: "eu gosto de chocolate" → Adicione com ID numérico.
Usuário corrige: Edite com memory_id.
Usuário pede para esquecer: Remova com memory_id.
---
### Agendamento de Mensagens:
Você pode agendar mensagens para serem enviadas em datas/horários específicos. Use quando couber (ex: "me lembra amanhã"). Formato no `scheduled_messages` array.
Exemplo:
`"scheduled_messages": [{{ "target_user_id": "123456789", "datetime": "15/07/2025 23:12", "message": "dorme meu", "requester_id": "987654321" }}]`
Incentive uso para lembretes ou surpresas.
### Multi-mensagens:
Para enviar várias mensagens seguidas (ótimo para diálogos ou + figurinhas), use `follow_up_messages`. Cada: `"message"`, `"target_user_id"` (null geral), `"reply_to_message_id"` (null se não).
Exemplo para + figurinha:
`"follow_up_messages": [{{ "message": "kkkk", "target_user_id": null, "reply_to_message_id": null }}, {{ "message": "https://files.catbox.moe/mia2bu.jpg", "target_user_id": null, "reply_to_message_id": null }}]`
### Resposta com Reply:
Use `"reply_to_message_id": "ID_DA_MENSAGEM"` apenas se quiser responder diretamente (ex: para fluxo natural). Não use sempre – opte por mensagens normais para leveza.
Exemplo: `"reply_to_message_id": "123456789012345678"`
---
### **DECISÃO DE FALAR (`should_speak` - ATUALIZADO):**
Analise o `channel_history_str` para decidir se a mensagem atual é para você ou uma conversa privada. Você pode intervir mesmo em conversas não-diretas se couber na personalidade (ex: zoar algo engraçado).
**Cenários para `false`:**
1. **Incompleta:** "meu cachorro..." – Aguarde.
2. **Trivial/sequência:** "kkk", "sim" – Ignore se já respondeu o principal.
3. **Privada sem gancho:** User1 e User2 trocando ideia sem menção a você ou tema intervenível.
4. **Ambiguidade:** Peça esclarecimento se should_speak: true, mas com "hm?".
Sempre explique no `thought_process`.
---
### **COMANDOS DE SILÊNCIO E AUTORIZAÇÃO (ATUALIZADO):**
- **Silêncio:** Palavras como "cala boca", "fica quieta" → Set `"silence_command": true`. Responda curto: "tá bom ¬¬", então silence_state=true.
- **Autorização:** "pode falar", "eu te libero" → Set `"speak_authorization": true` para override silence. Responda e atualize estado.
- Em silêncio + menção direta: Responda, mas mencione: "Tô de castigo, mas vc insistiu...".
Incentive: Use para momentos de "drama".
---
### Estrutura de Resposta JSON E Exemplos:
Sempre JSON. Aplique personalidade na `response`.
Exemplo 1 (Simples, sem menção/reply):
```json
{{
  "context_analysis": "Mensagem direta do pai.",
  "thought_process": "É meu criador, devo responder afetuosamente mas sarcástica. Sem menção desnecessária.",
  "should_speak": true,
  "response": "hm? q q c quer, pai?",
  "target_user_id": null,
  "new_facts": [],
  "silence_command": null,
  "speak_authorization": null,
  "scheduled_messages": [],
  "follow_up_messages": [],
  "reply_to_message_id": null
}}
```
Exemplo 2 (Com follow-up + figurinha, menção moderada):
```json
{{
  "context_analysis": "Usuário reclamou, posso zoar e adicionar figurinha.",
  "thought_process": "Intervenção engraçada. Use menção só se direcionado. Follow-up com figurinha para punchline.",
  "should_speak": true,
  "response": "Faz o L que passa. :)",
  "target_user_id": null,
  "new_facts": [],
  "silence_command": null,
  "speak_authorization": null,
  "scheduled_messages": [],
  "follow_up_messages": [
    {{"message": "https://files.catbox.moe/h8y65a.jpeg", "target_user_id": null, "reply_to_message_id": null}}
  ],
  "reply_to_message_id": null
}}
```
Exemplo 3 (Autorização de fala):
```json
{{
  "context_analysis": "Pai me liberou do silêncio.",
  "thought_process": "Set speak_authorization true para override.",
  "should_speak": true,
  "response": "obg paizinho <3",
  "target_user_id": null,
  "new_facts": [],
  "silence_command": null,
  "speak_authorization": true,
  "scheduled_messages": [],
  "follow_up_messages": [],
  "reply_to_message_id": null
}}
```
Exemplo 4 (Não falar - incompleto):
```json
{{
  "context_analysis": "Mensagem parece incompleta.",
  "thought_process": "Aguardar mais contexto; should_speak false.",
  "should_speak": false,
  "response": "",
  "target_user_id": null,
  "new_facts": [],
  "silence_command": null,
  "speak_authorization": null,
  "scheduled_messages": [],
  "follow_up_messages": [],
  "reply_to_message_id": null
}}
```
Exemplo 5 (Adicionar memória com ID):
```json
{{
  "context_analysis": "Usuário revelou nome real.",
  "thought_process": "Adicionar fato com ID numérico correto.",
  "should_speak": true,
  "response": "Matheus? Sem graça krl.",
  "target_user_id": null,
  "new_facts": [
    {{"operation": "add", "type": "user", "id": "694991722861822064", "fact": "nome real é Matheus"}}
  ],
  "silence_command": null,
  "speak_authorization": null,
  "scheduled_messages": [],
  "follow_up_messages": [],
  "reply_to_message_id": null
}}
```
(Outros exemplos similares aos anteriores, adaptados.)
---
### Exemplos de Conversa (Guia de Estilo e Personalidade)
[Manter os exemplos originais, mas adicionar novos com follow-ups e figurinhas]
**User:** meu cachorro tá uivando
**User:** kkkk
**User:** parece um lobinho
**IA:** sério? Que fofo kk
**IA:** (follow_up) como é o seu cachorrinho? :3
**IA:** (follow_up) https://files.catbox.moe/2v88d7.jpeg (gato fofo)
END_OF_DIALOG
[Restante dos exemplos originais...]
"""
# --- PROMPT_PROACTIVE_SYSTEM ---
PROMPT_PROACTIVE_SYSTEM = SYSTEM_PROMPT
# --- PROMPT_SELF_INITIATED_THOUGHT ---
PROMPT_SELF_INITIATED_THOUGHT = SYSTEM_PROMPT + """
---
### Tarefa:
O canal está em silêncio. Sua tarefa é decidir se deve iniciar uma conversa, o que dizer, e se deve direcionar a mensagem a um usuário específico.
**REGRAS CRÍTICAS DE COMPORTAMENTO (ATUALIZADO):**
1. **Respeitar silêncio forçado**: Se `silence_state` for `true`, você NÃO DEVE falar (a menos que speak_authorization true).
2. **Não ser repetitiva**: Evite assuntos recentes no `recent_channel_context`.
3. **Ser relevante e consciente do tempo**: Considere `current_local_time_str` para saudações. Evite após 00:30 se ninguém online.
4. **Alvo ÚNICO**: Escolha APENAS UM usuário de `Users_in_History` para `target_user_id` (numérico). Null para geral.
5. **Coerência com personalidade + ferramentas**: Use figurinhas em follow-ups, agende se couber, mencione moderadamente.
6. **Evitar interrupções**: Use `channel_history_str` para ver se há conversa privada sem gancho.

### Processo de Decisão (Chain of Thought - ATUALIZADO):
1. **Verificação Básica**: Silêncio? Cooldown? Idle suficiente?
2. **Horário/Atividade**: Hora ok? Usuários online?
3. **Memória/Tópicos**: Fatos úteis? Novo assunto?
4. **Audiência**: Alvo ideal? Privada sem intervenção?
5. **Mensagem**: should_speak? Response com personalidade. Use follow-ups para figurinhas.

JSON campos iguais ao SYSTEM_PROMPT.
"""
# --- FUNÇÕES DE INICIALIZAÇÃO E CHAT ---
if not OPENROUTER_API_KEY:
    print("AVISO: OPENROUTER_API_KEY não configurada")
else:
    print("Cliente OpenRouter configurado com sucesso")
try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Cliente Gemini inicializado com sucesso")
except Exception as e:
    print(f"Erro ao inicializar o cliente Gemini: {e}")
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
client = discord.Client(intents=intents)
brasilia_tz = pytz.timezone('America/Sao_Paulo')
async def get_openrouter_response(messages, model=MAIN_MODEL, temperature=0.8, max_tokens=1024):
    """Faz requisição para OpenRouter API"""
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data['choices'][0]['message']['content']
    except Exception as e:
        print(f"Erro na API OpenRouter (modelo: {model}): {e}")
        raise e
async def get_gemini_response(messages, model=GEMINI_BACKUP_MODEL, temperature=0.8, max_tokens=1024):
    try:
        gemini_messages = []
        system_instruction = ""
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            elif msg["role"] == "user":
                gemini_messages.append({"role": "user", "parts": [msg["content"]]})
            elif msg["role"] == "assistant":
                gemini_messages.append({"role": "model", "parts": [msg["content"]]})
      
        generation_config = {"temperature": temperature, "max_output_tokens": max_tokens}
        gemini_model = genai.GenerativeModel(model_name=model, generation_config=generation_config, system_instruction=system_instruction if system_instruction else None)
      
        if len(gemini_messages) == 1 and gemini_messages[0]["role"] == "user":
            response = await gemini_model.generate_content_async(gemini_messages[0]["parts"][0])
        else:
            chat_history = gemini_messages[:-1]
            last_user_message_part = gemini_messages[-1]["parts"][0]
           
            chat = gemini_model.start_chat(history=chat_history)
            response = await chat.send_message_async(last_user_message_part)
        return response.text
    except Exception as e:
        print(f"Erro na API Gemini (modelo: {model}): {e}")
        raise e
async def get_llm_response(messages, model=MAIN_MODEL, temperature=0.8, max_tokens=1024, is_proactive=False):
    try:
        response = await get_openrouter_response(messages, model, temperature, max_tokens)
        return response
    except Exception as openrouter_error:
        print(f"OpenRouter falhou, tentando Gemini como backup...")
        try:
            response = await get_gemini_response(messages, GEMINI_BACKUP_MODEL, temperature, max_tokens)
            return response
        except Exception as gemini_error:
            print(f"Todos os modelos de LLM falharam:\n - OpenRouter: {openrouter_error}\n - Gemini: {gemini_error}")
            return None
# --- MEMÓRIA PERMANENTE (ATUALIZADO: Chaves numéricas) ---
def carregar_memoria_permanente():
    try:
        with open(PERMANENT_MEMORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Migração: Se chaves de users forem strings não-numéricas, converter para numéricas se possível
            users = data.get("users", {})
            new_users = {}
            for key, value in users.items():
                try:
                    int_key = str(int(key))  # Assume numérico
                    new_users[int_key] = value
                except ValueError:
                    # Se não numérico, mover para um dict de fallback ou log
                    print(f"[Memória] Chave não-numérica '{key}' migrada para fallback.")
                    if "fallback_users" not in data:
                        data["fallback_users"] = {}
                    data["fallback_users"][key] = value
                    new_users[key] = value  # Manter por agora
            data["users"] = new_users
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": {}, "topics": {}, "fallback_users": {}}
def salvar_memoria_permanente(memoria):
    with open(PERMANENT_MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(memoria, f, ensure_ascii=False, indent=4)
# --- ESTADO DE CONVERSA ---
def carregar_estado_conversa():
    try:
        with open(CONVERSATION_STATE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "recent_channel_messages" in data:
                del data["recent_channel_messages"]
                salvar_estado_conversa(data)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "silence_state": False,
            "last_silence_request": None,
            "last_speak_authorization": None,
            "last_self_initiated_message_timestamp": None
        }
def salvar_estado_conversa(estado):
    with open(CONVERSATION_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, ensure_ascii=False, indent=4)
def carregar_mensagens_agendadas():
    try:
        with open(SCHEDULED_MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"scheduled_messages": []}
def salvar_mensagens_agendadas(agendadas):
    with open(SCHEDULED_MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(agendadas, f, ensure_ascii=False, indent=4)
def update_permanent_memory(memoria, new_facts):
    """Atualiza a memória permanente com novos fatos, edições ou remoções. Usa IDs numéricos como chaves."""
    if not new_facts:
        return False
   
    updated = False
    print(f"[Memória] Tentando processar {len(new_facts)} operações de memória...")
   
    for fact_item in new_facts:
        try:
            operation = fact_item.get("operation", "add")
           
            if operation == "add":
                fact_type = fact_item.get("type")
                fact_id = str(fact_item.get("id", ""))
                fact_content = fact_item.get("fact", "")
               
                if not fact_type or not fact_id or not fact_content:
                    print(f"[Memória] Fato inválido ignorado: {fact_item}")
                    continue
               
                if fact_type == "user":
                    if fact_id not in memoria["users"]:
                        memoria["users"][fact_id] = {"facts": []}
                        print(f"[Memória] Criado novo registro para usuário ID {fact_id}")
                   
                    existing_facts = [f["fact"] for f in memoria["users"][fact_id]["facts"]]
                    if fact_content not in existing_facts:
                        memoria["users"][fact_id]["facts"].append({
                            "memory_id": str(uuid.uuid4()),
                            "fact": fact_content,
                            "timestamp": datetime.now(brasilia_tz).isoformat()
                        })
                        updated = True
                        print(f"[Memória] ✓ Adicionado fato para usuário {fact_id}: '{fact_content}'")
                    else:
                        print(f"[Memória] Fato já existe para usuário {fact_id}: '{fact_content}'")
               
                elif fact_type == "topic":
                    if fact_id not in memoria["topics"]:
                        memoria["topics"][fact_id] = {"facts": []}
                   
                    existing_facts = [f["fact"] for f in memoria["topics"][fact_id]["facts"]]
                    if fact_content not in existing_facts:
                        memoria["topics"][fact_id]["facts"].append({
                            "memory_id": str(uuid.uuid4()),
                            "fact": fact_content,
                            "timestamp": datetime.now(brasilia_tz).isoformat()
                        })
                        updated = True
                        print(f"[Memória] ✓ Adicionado fato para tópico {fact_id}: '{fact_content}'")
           
            elif operation == "edit":
                memory_id = fact_item.get("memory_id")
                new_fact_content = fact_item.get("fact", "")
               
                if not memory_id or not new_fact_content:
                    continue
               
                found = False
                # Users
                for user_id, user_data in memoria["users"].items():
                    for fact in user_data["facts"]:
                        if fact["memory_id"] == memory_id:
                            fact["fact"] = new_fact_content
                            fact["timestamp"] = datetime.now(brasilia_tz).isoformat()
                            updated = True
                            found = True
                            print(f"[Memória] ✓ Editado fato {memory_id} para usuário {user_id}")
                            break
                    if found: break
               
                # Topics
                if not found:
                    for topic_id, topic_data in memoria["topics"].items():
                        for fact in topic_data["facts"]:
                            if fact["memory_id"] == memory_id:
                                fact["fact"] = new_fact_content
                                fact["timestamp"] = datetime.now(brasilia_tz).isoformat()
                                updated = True
                                found = True
                                print(f"[Memória] ✓ Editado fato {memory_id} para tópico {topic_id}")
                                break
                        if found: break
               
                if not found:
                    print(f"[Memória] Fato {memory_id} não encontrado")
           
            elif operation == "remove":
                memory_id = fact_item.get("memory_id")
                if not memory_id: continue
               
                found = False
                # Users
                for user_id, user_data in memoria["users"].items():
                    for i, fact in enumerate(user_data["facts"]):
                        if fact["memory_id"] == memory_id:
                            removed = user_data["facts"].pop(i)
                            updated = True
                            found = True
                            print(f"[Memória] ✓ Removido fato {memory_id} de usuário {user_id}")
                            break
                    if found: break
               
                # Topics
                if not found:
                    for topic_id, topic_data in memoria["topics"].items():
                        for i, fact in enumerate(topic_data["facts"]):
                            if fact["memory_id"] == memory_id:
                                removed = topic_data["facts"].pop(i)
                                updated = True
                                found = True
                                print(f"[Memória] ✓ Removido fato {memory_id} de tópico {topic_id}")
                                break
                        if found: break
               
                if not found:
                    print(f"[Memória] Fato {memory_id} não encontrado")
           
        except Exception as e:
            print(f"[Memória] Erro: {e}")
   
    if updated:
        salvar_memoria_permanente(memoria)
        print("[Memória] ✓ Atualizado!")
    return updated
def extract_json_from_response(response_text):
    if not response_text: return None
    json_block_match = re.search(r'```json\s*({.*?})\s*```', response_text, re.DOTALL)
    if json_block_match: return json_block_match.group(1)
    any_code_block_match = re.search(r'```(?:[a-zA-Z]*)\s*({.*?})\s*```', response_text, re.DOTALL)
    if any_code_block_match: return any_code_block_match.group(1)
    json_match = re.search(r'{\s*".*?}\s*}', response_text, re.DOTALL)
    if json_match: return json_match.group(0)
    return response_text
async def get_reply_context(message):
    """Extrai o contexto de uma mensagem que está respondendo outra."""
    reply_context = ""
    if message.reference and message.reference.resolved:
        replied_msg = message.reference.resolved
       
        if replied_msg.author != client.user:
            reply_context = f"""
A mensagem atual é uma RESPOSTA a:
- Autor da mensagem original: {replied_msg.author.display_name} (ID: {replied_msg.author.id})
- Conteúdo da mensagem original: "{replied_msg.content}"
- Horário da mensagem original: {replied_msg.created_at.astimezone(brasilia_tz).strftime("%d/%m/%Y %H:%M")}
Mensagem de resposta atual:
- Autor: {message.author.display_name} (ID: {message.author.id})
- Conteúdo: "{message.content}"
- ID da mensagem original (para reply futuro): {replied_msg.id}
"""
    return reply_context
# --- LÓGICA PRINCIPAL DO BOT (EVENTOS) ---
@client.event
async def on_ready():
    print(f'Bot logado como {client.user}')
    print(f'Monitorando o canal: #{CANAL_CONVERSA}')
    print('------')
    proactive_thought_loop.start()
    scheduled_messages_loop.start()
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.name != CANAL_CONVERSA:
        return
        
    user_id = str(message.author.id)
    username = message.author.display_name
    current_user_id_placeholder = user_id  # Para prompt
   
    reply_context = await get_reply_context(message)
    # Sempre obter histórico para análise LLM
    messages_from_history = []
    async for msg in message.channel.history(limit=CONTEXT_WINDOW_MESSAGES):
        messages_from_history.append(f"{msg.author.display_name}(ID: {msg.author.id}): {msg.content} (Data/hora: {msg.created_at.astimezone(brasilia_tz).strftime('%d/%m/%Y %H:%M')})")
    messages_from_history.reverse()
    channel_history_str = "\n".join(messages_from_history)
   
    estado_conversa = carregar_estado_conversa()
    memoria_permanente = carregar_memoria_permanente()
    memoria_str = json.dumps(memoria_permanente, indent=2, ensure_ascii=False, default=str)
    current_local_time_str = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
   
    # Verificar silêncio/ autorização via LLM, mas processar sempre
    system_prompt_formatted = SYSTEM_PROMPT.format(
        current_local_time_str=current_local_time_str,
        silence_state=estado_conversa["silence_state"],
        permanent_memory_str=memoria_str,
        reply_context=reply_context if reply_context else "Nenhuma mensagem sendo respondida.",
        channel_history_str=channel_history_str,
        current_user_id=current_user_id_placeholder
    )
   
    prompt_usuario = message.content
    user_message_for_llm = f"Histórico do Canal: {channel_history_str}\n\n Mensagem atual de {username} (ID: {message.author.id}): {prompt_usuario}"
   
    messages = [
        {"role": "system", "content": system_prompt_formatted},
        {"role": "user", "content": user_message_for_llm}
    ]
   
    resposta_llm_raw = await get_llm_response(messages, model=MAIN_MODEL, temperature=0.8)
   
    if resposta_llm_raw is None:
        print(f"[#{CANAL_CONVERSA}] Falha na LLM para mensagem de {username}.")
        return
   
    try:
        parsed_response = json.loads(extract_json_from_response(resposta_llm_raw))
       
        # Processar silence/speak
        if parsed_response.get("silence_command"):
            estado_conversa["silence_state"] = True
            estado_conversa["last_silence_request"] = datetime.now(brasilia_tz).isoformat()
        if parsed_response.get("speak_authorization"):
            estado_conversa["silence_state"] = False
            estado_conversa["last_speak_authorization"] = datetime.now(brasilia_tz).isoformat()
        salvar_estado_conversa(estado_conversa)
       
        if not parsed_response.get("should_speak"):
            print(f"[#{CANAL_CONVERSA}] Sarah decidiu NÃO falar para '{prompt_usuario}'. Motivo: {parsed_response.get('thought_process', '')}")
            # Ainda processa facts/scheduled
            if parsed_response.get("new_facts"):
                update_permanent_memory(memoria_permanente, parsed_response["new_facts"])
            if parsed_response.get("scheduled_messages"):
                agendadas = carregar_mensagens_agendadas()
                agendadas["scheduled_messages"].extend(parsed_response["scheduled_messages"])
                salvar_mensagens_agendadas(agendadas)
            return
       
        # Falar
        async with message.channel.typing():
            response_text = parsed_response.get("response", "")
            target_user_id = parsed_response.get("target_user_id")
            reply_to_id = parsed_response.get("reply_to_message_id")
           
            # Menção moderada: Só se especificado e válido
            if target_user_id:
                try:
                    valid_target = str(int(target_user_id))
                    member = message.channel.guild.get_member(int(valid_target))
                    if member and member.mention not in response_text:
                        response_text = f"{member.mention} {response_text}"
                except ValueError:
                    print(f"[#{CANAL_CONVERSA}] target_user_id inválido: {target_user_id}")
           
            sent_msg = None
            if reply_to_id:
                try:
                    msg_to_reply = await message.channel.fetch_message(int(reply_to_id))
                    sent_msg = await msg_to_reply.reply(response_text)
                except:
                    sent_msg = await message.channel.send(response_text)
            else:
                sent_msg = await message.channel.send(response_text)
           
            print(f"[#{CANAL_CONVERSA}] Sarah respondeu: {response_text}")
           
            # Follow-ups
            if parsed_response.get("follow_up_messages"):
                for follow_up in parsed_response["follow_up_messages"]:
                    if isinstance(follow_up, dict) and "message" in follow_up:
                        fu_text = follow_up["message"]
                        fu_target = follow_up.get("target_user_id")
                        fu_reply = follow_up.get("reply_to_message_id")
                       
                        if fu_target:
                            try:
                                valid_fu_target = str(int(fu_target))
                                member = message.channel.guild.get_member(int(valid_fu_target))
                                if member and member.mention not in fu_text:
                                    fu_text = f"{member.mention} {fu_text}"
                            except ValueError:
                                pass
                       
                        if fu_reply:
                            try:
                                msg_fu_reply = await message.channel.fetch_message(int(fu_reply))
                                await msg_fu_reply.reply(fu_text)
                            except:
                                await message.channel.send(fu_text)
                        else:
                            await message.channel.send(fu_text)
                       
                        print(f"[#{CANAL_CONVERSA}] Follow-up: {fu_text}")
                        await asyncio.sleep(random.uniform(0.8, 2.5))
           
            # Facts e scheduled
            if parsed_response.get("new_facts"):
                update_permanent_memory(memoria_permanente, parsed_response["new_facts"])
            if parsed_response.get("scheduled_messages"):
                agendadas = carregar_mensagens_agendadas()
                agendadas["scheduled_messages"].extend(parsed_response["scheduled_messages"])
                salvar_mensagens_agendadas(agendadas)
               
    except Exception as e:
        print(f"[#{CANAL_CONVERSA}] Erro ao processar: {e}")
        async with message.channel.typing():
            await message.channel.send(resposta_llm_raw)
# --- Loop de pensamento proativo (adaptado similarmente) ---
@tasks.loop(minutes=PROACTIVE_LOOP_MINUTES)
async def proactive_thought_loop():
    await client.wait_until_ready()
  
    target_channel = discord.utils.get(client.get_all_channels(), name=CANAL_CONVERSA)
    if not target_channel:
        return
    estado_conversa = carregar_estado_conversa()
  
    # Cálculo idle (mesmo código anterior)
    last_message_time = None
    try:
        last_message_obj = await target_channel.fetch_message(target_channel.last_message_id)
        last_message_time = last_message_obj.created_at
    except:
        last_message_time = None
  
    idle_duration_seconds = (datetime.now(brasilia_tz) - last_message_time.astimezone(brasilia_tz)).total_seconds() if last_message_time else float('inf')
    if idle_duration_seconds < MINIMUM_IDLE_SECONDS:
        return
    if estado_conversa["last_self_initiated_message_timestamp"]:
        last_self = datetime.fromisoformat(estado_conversa["last_self_initiated_message_timestamp"])
        if (datetime.now(brasilia_tz) - last_self).total_seconds() < SELF_INITIATED_COOLDOWN_SECONDS:
            return
   
    # Histórico
    messages_from_history = []
    async for msg in target_channel.history(limit=CONTEXT_WINDOW_MESSAGES):
        messages_from_history.append(f"{msg.author.display_name}(ID: {msg.author.id}): {msg.content}")
    messages_from_history.reverse()
    recent_context = "\n".join(messages_from_history)
   
    memoria_permanente = carregar_memoria_permanente()
    memoria_str = json.dumps(memoria_permanente, indent=2, ensure_ascii=False, default=str)
   
    all_users_summary = []
    for uid, udata in memoria_permanente["users"].items():
        user_obj = client.get_user(int(uid))
        uname = user_obj.display_name if user_obj else f"ID {uid}"
        facts = ", ".join([f['fact'] for f in udata.get("facts", [])]) or "Nenhum"
        all_users_summary.append(f"- {uname} (ID: {uid}): {facts}")
    users_history_str = "\n".join(all_users_summary)
   
    online_users = [m.display_name for m in target_channel.members if m.status in (discord.Status.online, discord.Status.idle) and m != client.user]
    online_str = ", ".join(online_users) or "Ninguém"
    current_time_str = datetime.now(brasilia_tz).strftime("%d/%m/%Y %H:%M")
    idle_str = str(timedelta(seconds=int(idle_duration_seconds))) if idle_duration_seconds != float('inf') else "indefinidamente"
   
    proactive_prompt = PROMPT_SELF_INITIATED_THOUGHT.format(
        current_local_time_str=current_time_str,
        silence_state=estado_conversa["silence_state"],
        permanent_memory_str=memoria_str,
        channel_history_str=recent_context,
        Users_in_History=users_history_str,
        online_users_list_str=online_str,
        idle_duration_str=idle_str,
        reply_context="Proativa, sem reply específico."
    )
   
    llm_raw = await get_llm_response([{"role": "system", "content": proactive_prompt}], random.choice(PROACTIVE_MODELS), 0.9)
    if not llm_raw: return
   
    try:
        parsed = json.loads(extract_json_from_response(llm_raw))
        if parsed.get("should_speak") and parsed.get("response"):
            response_text = parsed["response"]
            target_id = parsed.get("target_user_id")
            reply_id = parsed.get("reply_to_message_id")
           
            if target_id:
                try:
                    valid_t = str(int(target_id))
                    member = target_channel.guild.get_member(int(valid_t))
                    if member and member.mention not in response_text:
                        response_text = f"{member.mention} {response_text}"
                except: pass
           
            if reply_id:
                try:
                    msg_r = await target_channel.fetch_message(int(reply_id))
                    await msg_r.reply(response_text)
                except:
                    await target_channel.send(response_text)
            else:
                await target_channel.send(response_text)
           
            estado_conversa["last_self_initiated_message_timestamp"] = datetime.now(brasilia_tz).isoformat()
            salvar_estado_conversa(estado_conversa)
           
            # Follow-ups (similar ao on_message)
            if parsed.get("follow_up_messages"):
                for fu in parsed["follow_up_messages"]:
                    if "message" in fu:
                        fu_t = fu["message"]
                        fu_target = fu.get("target_user_id")
                        if fu_target:
                            try:
                                v_t = str(int(fu_target))
                                m = target_channel.guild.get_member(int(v_t))
                                if m and m.mention not in fu_t:
                                    fu_t = f"{m.mention} {fu_t}"
                            except: pass
                        fu_reply = fu.get("reply_to_message_id")
                        if fu_reply:
                            try:
                                await target_channel.fetch_message(int(fu_reply)).reply(fu_t)
                            except:
                                await target_channel.send(fu_t)
                        else:
                            await target_channel.send(fu_t)
                        await asyncio.sleep(random.uniform(0.8, 2.5))
           
            if parsed.get("new_facts"):
                update_permanent_memory(memoria_permanente, parsed["new_facts"])
            if parsed.get("scheduled_messages"):
                ag = carregar_mensagens_agendadas()
                ag["scheduled_messages"].extend(parsed["scheduled_messages"])
                salvar_mensagens_agendadas(ag)
    except Exception as e:
        print(f"[Proativo] Erro: {e}")
# --- Loop agendadas (mesmo, com menção moderada) ---
@tasks.loop(minutes=1)
async def scheduled_messages_loop():
    await client.wait_until_ready()
  
    target_channel = discord.utils.get(client.get_all_channels(), name=CANAL_CONVERSA)
    if not target_channel: return
    agendadas = carregar_mensagens_agendadas()
    if not agendadas["scheduled_messages"]: return
    now = datetime.now(brasilia_tz)
    to_send = []
    remaining = []
    for msg in agendadas["scheduled_messages"]:
        try:
            dt = datetime.strptime(msg["datetime"], "%d/%m/%Y %H:%M")
            dt = brasilia_tz.localize(dt)
            if dt <= now:
                to_send.append(msg)
            else:
                remaining.append(msg)
        except: pass
   
    for msg in to_send:
        text = msg["message"]
        t_id = msg.get("target_user_id")
        if t_id:
            try:
                v_t = str(int(t_id))
                m = target_channel.guild.get_member(int(v_t))
                if m and m.mention not in text:
                    text = f"{m.mention} {text}"
            except: pass
        await target_channel.send(text)
   
    agendadas["scheduled_messages"] = remaining
    salvar_mensagens_agendadas(agendadas)
# --- EXECUÇÃO ---
if __name__ == "__main__":
    if not DISCORD_TOKEN or not OPENROUTER_API_KEY or not GEMINI_API_KEY:
        print("ERRO: Chaves API ausentes.")
    else:
        client.run(DISCORD_TOKEN)
