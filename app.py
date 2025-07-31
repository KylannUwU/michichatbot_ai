import os
import openai
import time
import asyncio
import json
import aiohttp
from twitchio.ext import commands
from dotenv import load_dotenv

load_dotenv()

archivo_contexto = "contexto_conversacion.json"
TIEMPO_REINICIO = 300

openai.api_key = os.getenv('OPENAI_API_KEY')
twitch_token = os.getenv('Twitch_OAUTH_TOKEN')
twitch_client_id = os.getenv('Twitch_CLIENT_ID')

if not openai.api_key or not twitch_token or not twitch_client_id:
    print("Error: Variables de entorno faltantes.")
    exit()

ALLOWED_USERS = ['user1', 'user2']
SALUDO_KEYWORDS = ['hola', 'ola', 'holi', 'alo','buenas', 'hi', 'onda']
CATEGORIA_KEYWORDS = ['categoria', 'categoría']
VIEWERS_KEYWORDS = ['viewers on', 'cheap viewers on', 'cheap viewers', 'espectadores gratis para ti']
SECRET_KEYWORDS = {'Radiante de Corazón': True}

def cargar_contexto():
    try:
        with open(archivo_contexto, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def guardar_contexto(contexto):
    with open(archivo_contexto, 'w') as file:
        json.dump(contexto, file, indent=4)

def obtener_respuesta_openai(contexto, pregunta):
    try:
        mensajes = [{"role": "system", "content": "Eres un asistente útil. Responde de manera clara y breve, conservando el contexto y SUPER IMPORTANTE no utilices mas de 460 caracteres."}]
        for mensaje in contexto.get('conversacion', []):
            mensajes.append({"role": "user", "content": mensaje['pregunta']})
            mensajes.append({"role": "assistant", "content": mensaje['respuesta']})
        mensajes.append({"role": "user", "content": pregunta})
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini-2024-07-18",
            messages=mensajes
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error al obtener respuesta de OpenAI: {e}")
        return "Lo siento, no pude generar una respuesta en este momento."

async def is_twitch_live(channel_name, client_id, oauth_token):
    url = f'https://api.twitch.tv/helix/streams?user_login={channel_name}'
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {oauth_token}'
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            data = await response.json()
            return len(data.get('data', [])) > 0

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(token=twitch_token, prefix='!', initial_channels=['NolleyRCC'])
        self.hola_counters = {}
        self.last_pendejon_time = 0
        self.last_suggestion_time = 0
        self.active = False
        self.temporal_shutdown = False
        self.stream_live = False
        self.offline_counter = 0
        self.loop.create_task(self.send_timers_from_json())
        self.loop.create_task(self.monitor_stream_status())

    async def monitor_stream_status(self):
        await self.wait_for_ready()
        while True:
            try:
                is_live = await is_twitch_live('NolleyRCC', twitch_client_id, twitch_token)
                channel = self.get_channel('NolleyRCC')
                if is_live:
                    if not self.stream_live:
                        if channel:
                            await channel.send("Bienvenidos al Stream nolleyClap")
                        self.active = True
                        self.stream_live = True
                        self.offline_counter = 0
                else:
                    if self.stream_live:
                        self.offline_counter += 1
                        if self.offline_counter >= 2:
                            if channel:
                                await channel.send("Buenas noches gente nolleyManrLove")
                            self.active = False
                            self.stream_live = False
                            self.offline_counter = 0
                    else:
                        self.offline_counter += 1
            except Exception as e:
                print(f"Error verificando estado del stream: {e}")
            await asyncio.sleep(120)

    async def send_timers_from_json(self):
        await self.wait_for_ready()
        channel = self.get_channel('NolleyRCC')
        if not channel:
            print("Error: No se pudo obtener el canal.")
            return

        try:
            with open("timers.json", "r", encoding="utf-8") as f:
                timers = json.load(f)
        except Exception as e:
            print(f"Error al cargar timers.json: {e}")
            return

        for i, timer in enumerate(timers):
            mensaje = timer["mensaje"]
            intervalo = timer["intervalo"] * 60
            delay_inicial = i * 240
            self.loop.create_task(self.repetidor_mensaje(channel, mensaje, intervalo, delay_inicial))



    async def repetidor_mensaje(self, channel, mensaje, intervalo, delay_inicial):
        await asyncio.sleep(delay_inicial)
        while True:
            if self.active:
                try:
                    await channel.send(mensaje)
                except Exception as e:
                    print(f"Error al enviar mensaje: {e}")
            await asyncio.sleep(intervalo)

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    async def send_hello_chat(self):
        await self.wait_for_ready()
        channel = self.get_channel('NolleyRCC')
        if not channel:
            print("Error: No se pudo obtener el canal.")
            return
        while True:
            await asyncio.sleep(1200)
            if self.active:
                try:
                    await channel.send("Recuerden que hay alertas especiales desde poco mas de los 10 bits, prueba tu suerte nolleyClap (Sugiero la de 86 bits)")
                except Exception as e:
                    print(f"Error al enviar el primer mensaje: {e}")
            await asyncio.sleep(1200)
            if self.active:
                try:
                    await channel.send("NUEVOS EMOTES wiwi Recuerden que para poder verlos deben tener la extension de 7TV, esta la pueden encontrar aca https://7tv.app/ nolleyChupiChupi")
                except Exception as e:
                    print(f"Error al enviar el segundo mensaje: {e}")

    async def handle_secret_words(self, message):
        message_content = message.content.lower()
        if message.author.name.lower() != 'nightbot':
            for secret_word in SECRET_KEYWORDS:
                if not SECRET_KEYWORDS[secret_word] and secret_word.lower() in message_content:
                    SECRET_KEYWORDS[secret_word] = True
                    await message.channel.send(f'Palabra secreta encontrada por {message.author.name}, {secret_word} nolleyHype.')

    async def handle_greetings(self, message):
        message_content = message.content.lower()
        if any(keyword in message_content for keyword in SALUDO_KEYWORDS):
            user_name = message.author.name.lower()
            self.hola_counters[user_name] = self.hola_counters.get(user_name, 0) + 1
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=[{
                        "role": "user",
                        "content": f"El siguiente mensaje es un saludo o no: '{message_content}' Responde con 'saludo' o 'no saludo'."
                    }]
                )
                ai_response = response.choices[0].message['content'].strip().lower()
                if ai_response == 'saludo':
                    if self.hola_counters[user_name] == 1:
                        await message.channel.send(f'Holaaaa, {message.author.name}, bienvenute al stream nolleyHug')
                    elif self.hola_counters[user_name] == 2:
                        await message.channel.send(f'Holaaaa {message.author.name} retornable')
            except Exception as e:
                print(f"Error al consultar a OpenAI: {e}")

    async def handle_category_suggestions(self, message):
        message_content = message.content.lower()
        if self.nick.lower() in message_content and any(keyword in message_content for keyword in CATEGORIA_KEYWORDS):
            current_time = time.time()
            if current_time - self.last_suggestion_time < 30:
                await message.channel.send(f'{message.author.name}, espera un poco antes de usar el comando nuevamente.')
                return
            words = message_content.split()
            last_word = words[-1].lower() if words else ''
            if message.author.is_mod or message.author.name.lower() in [user.lower() for user in ALLOWED_USERS]:
                if last_word == 'jc':
                    await message.channel.send('!jc')
                else:
                    await message.channel.send(f'!game {last_word}')
            else:
                await message.channel.send(f'@NolleyRCC el usuario {message.author.name} sugiere que la categoría debería ser {last_word}. ¿Es esto correcto?')
            self.last_suggestion_time = current_time

    async def handle_spams(self, message):
        msgcontent = message.content.strip()
        try:
            classification_response = openai.ChatCompletion.create(
                model="gpt-4o-mini-2024-07-18",
                messages=[
                    {"role": "system", "content": "Eres un asistente que clasifica contenido."},
                    {"role": "user", "content": f"{msgcontent}"}
                ]
            )
            classification = classification_response.choices[0].message['content'].strip().lower()
            return classification == "spam"
        except Exception as e:
            print(f"Error clasificando mensaje: {e}")
            return False

    async def handle_viewers_spam(self, message):
        message_content = message.content.lower()
        if message.first:
            is_spam = await self.handle_spams(message)
            if is_spam:
                channel = message.channel
                if channel:
                    await channel.send(f'!sacrificio @{message.author.name}')

    async def handle_questions(self, message):
        if self.nick.lower() in message.content.lower():
            pregunta = message.content.strip()
            contexto = cargar_contexto()
            tiempo_actual = time.time()
            timestamp_ultimo_reinicio = contexto.get("ultimo_reinicio", 0)
            if tiempo_actual - timestamp_ultimo_reinicio > TIEMPO_REINICIO:
                contexto = {"ultimo_reinicio": tiempo_actual, "conversacion": []}
            respuesta = obtener_respuesta_openai(contexto, pregunta)
            contexto.setdefault('conversacion', []).append({'pregunta': pregunta, 'respuesta': respuesta})
            contexto['ultimo_reinicio'] = tiempo_actual
            guardar_contexto(contexto)
            await message.channel.send(respuesta)

    async def event_cheer(self, cheer):
        print(f"Bits detectados")
        username = cheer.user.name
        amount = cheer.bits
        channel = cheer.channel

        if channel:
            print(f"Bits detectados")
            try:
                await channel.send(f"Gracias por los {amount} bits {username} nolleyBits")
            except Exception as e:
                print(f"Error al agradecer los bits: {e}")

    async def event_message(self, message):

        if message.author is None or message.author.name.lower() in [self.nick.lower(), 'nightbot']:
            return
        if message.author.name.lower() == "streamelements":
            if "is live" in message.content.lower() or "is on" in message.content.lower():
                self.temporal_shutdown = False
                return
        if self.temporal_shutdown:
            return
        if not self.active:
            return
        await self.handle_secret_words(message)
        await self.handle_greetings(message)
        await self.handle_category_suggestions(message)
        await self.handle_viewers_spam(message)
        await self.handle_questions(message)
        await self.handle_commands(message)


    @commands.command(name='respuesta')
    async def respuesta(self, ctx, *, pregunta: str):
        if self.nick.lower() not in ctx.message.content.lower():
            return
        contexto = cargar_contexto()
        tiempo_actual = time.time()
        timestamp_ultimo_reinicio = contexto.get("ultimo_reinicio", 0)
        if tiempo_actual - timestamp_ultimo_reinicio > TIEMPO_REINICIO:
            contexto = {"ultimo_reinicio": tiempo_actual, "conversacion": []}
        respuesta = obtener_respuesta_openai(contexto, pregunta)
        contexto.setdefault('conversacion', []).append({'pregunta': pregunta, 'respuesta': respuesta})
        contexto['ultimo_reinicio'] = tiempo_actual
        guardar_contexto(contexto)
        await ctx.send(respuesta)

    @commands.command(name='pendejon')
    async def pendejon(self, ctx):
        current_time = time.time()
        if current_time - self.last_pendejon_time < 10:
            await ctx.send(f'{ctx.author.name}, por favor espera unos segundos antes de usar el comando nuevamente.')
            return
        self.last_pendejon_time = current_time
        await ctx.send(f'@{ctx.author.name} Pendejon')

    @commands.command(name='activate')
    async def activate(self, ctx):
        if ctx.author.name.lower() == 'nightbot':
            await ctx.send(f'{ctx.author.name}, no puedes activar el bot.')
            return
        self.active = True
        await ctx.send(f'{ctx.author.name}, el bot ha sido activado.')

    @commands.command(name='deactivate')
    async def deactivate(self, ctx):
        if ctx.author.name.lower() == 'nightbot':
            await ctx.send(f'{ctx.author.name}, no puedes desactivar el bot.')
            return
        self.active = False
        await ctx.send(f'{ctx.author.name}, el bot ha sido desactivado.')

    @commands.command(name='tm')
    async def tm(self, ctx):
        self.temporal_shutdown = True
    
if __name__ == "__main__":
    bot = Bot()
    bot.run()
