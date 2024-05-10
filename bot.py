import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime, timezone, timedelta
import requests
import random
import aiomysql


# Configura los intents para habilitar todos los intents predeterminados
intents = discord.Intents.all()

# Configura el prefijo de los comandos
bot = commands.Bot(command_prefix='!', intents=intents, ws_response_timeout=120)  # Aumenta el tiempo de espera a 120 segundos

# Canal donde se enviará el mensaje
canal_id = 1230738046811639881  # Reemplaza esto con el ID de tu canal
#paralogin
DB_HOST = 'xxxxxxxxxxxxxxxx'
DB_PORT = xxxxx
DB_USER = 'xxxxxxxxxxxxxxxxxxxxxxxxxxx'
DB_PASSWORD = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
DB_NAME = 'xxxxxxxxxxxxxxxxxxxxxx'

# Diccionario para almacenar los contadores de cada personaje
craftie_counters = {
    "Vendoempanada": 71,
    "Vendochipa": 71,
    "Vendosopaipilla": 71
}

# Diccionario para almacenar las tareas programadas de cada personaje
craftie_tasks = {
    "Vendoempanada": None,
    "Vendochipa": None,
    "Vendosopaipilla": None
}

# Diccionario para almacenar la hora de inicio de cada tarea programada
task_start_times = {
    "Vendoempanada": None,
    "Vendochipa": None,
    "Vendosopaipilla": None
}

#función para enviar el mensaje para un personaje específico
async def enviar_mensaje_personaje(personaje):
    canal = bot.get_channel(canal_id)
    await asyncio.sleep(craftie_counters[personaje] * 3600)  # Espera el tiempo definido en el contador
    await canal.send(f"¡El foco ya se llenó para {personaje}! <@&1234734461346906165>")

# función para reiniciar la tarea programada de un personaje específico
def reiniciar_tarea_programada(personaje):
    horas = craftie_counters[personaje]
    if craftie_tasks[personaje] is not None:
        craftie_tasks[personaje].cancel()
    craftie_tasks[personaje] = tasks.loop(hours=horas)(enviar_mensaje_personaje_task(personaje))
    task_start_times[personaje] = datetime.now(timezone.utc)  # Guarda la hora de inicio de la tarea
    craftie_tasks[personaje].start()

#función que devuelve una corutina que llamará a enviar_mensaje_personaje con el argumento personaje
def enviar_mensaje_personaje_task(personaje):
    async def task():
        await enviar_mensaje_personaje(personaje)
    return task
#para reiniciar el contador de un personaje
@bot.command()
async def craftie(ctx, personaje):
    personaje = personaje.capitalize()  # Convertir la primera letra en mayúscula para que coincida con las claves del diccionario
    if personaje not in craftie_counters:
        await ctx.send("Personaje no válido. Los personajes disponibles son Vendoempanada, Vendochipa y Vendosopaipilla.")
        return
    reiniciar_tarea_programada(personaje)  # No es necesario convertir a minúsculas aca
    await ctx.send(f"El timer para {personaje} ha sido reiniciado.")

# comando !timeto para mostrar cuánto tiempo queda para cada personaje
@bot.command()
async def timeto(ctx):
    ahora = datetime.now(timezone.utc)
    for personaje, horas_restantes in craftie_counters.items():
        if task_start_times[personaje] is not None:
            # Calcula el tiempo transcurrido desde que se inició la tarea programada
            tiempo_transcurrido = ahora - task_start_times[personaje]
            # Calcula cuántos ciclos completos de la tarea han pasado
            ciclos_completos = tiempo_transcurrido // timedelta(hours=horas_restantes)
            # Calcula el tiempo restante ajustado
            tiempo_restante = timedelta(hours=horas_restantes) - (tiempo_transcurrido - ciclos_completos * timedelta(hours=horas_restantes))
            await ctx.send(f"Para {personaje} faltan aproximadamente {tiempo_restante}.")
        else:
            await ctx.send(f"No se ha iniciado la tarea para {personaje}.")

# Define un evento para cuando el bot esté listo
@bot.event
async def on_ready():
    print(f'¡{bot.user.name} está listo!')
    # Conectarse a la base de datos y crear la tabla blacklist si no existe
    connection = await aiomysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        autocommit=True
    )
    await create_blacklist_table(connection)
    connection.close()

    # Inicia las tareas programadas para cada personaje
    for personaje in craftie_counters:
        reiniciar_tarea_programada(personaje)

#función para crear la tabla blacklist si no existe
async def create_blacklist_table(connection):
    async with connection.cursor() as cursor:
        # Verificar si la tabla blacklist ya existe
        await cursor.execute("SHOW TABLES LIKE 'blacklist'")
        exists = await cursor.fetchone()

        if not exists:
            # Si la tabla no existe la crea
            await cursor.execute(
                """
                CREATE TABLE blacklist (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    nombre VARCHAR(255),
                    motivo TEXT,
                    fecha DATE,
                    oficial VARCHAR(255)
                )
                """
            )
            print("La tabla 'blacklist' ha sido creada exitosamente.")


# para testear si funca el bot
@bot.command()
async def ping(ctx):
    await ctx.send('!pong')

@bot.command()
async def who(ctx, nombre):
    url = f"https://gameinfo.albiononline.com/api/gameinfo/search?q={nombre}"
    response = requests.get(url)
    data = response.json()

    if data.get('players'):
        player_info = data['players'][0]

        # Accede a los datos utilizando get() para evitar errores si las claves no están presentes
        kill_fame = "{:,}".format(player_info.get('KillFame', 0))
        death_fame = "{:,}".format(player_info.get('DeathFame', 0))
        fame_ratio = player_info.get('FameRatio', 'No disponible')
        guild_name = player_info.get('GuildName', 'Sin gremio')
        alliance_name = player_info.get('AllianceName', '')

        # Crear un mensaje embed
        embed = discord.Embed(title=f"Información sobre {nombre}", color=discord.Color.green())
        embed.add_field(name="Kill Fame", value=kill_fame, inline=True)
        embed.add_field(name="Death Fame", value=death_fame, inline=True)
        embed.add_field(name="Fame Ratio", value=fame_ratio, inline=True)
        embed.add_field(name="Guild", value=guild_name, inline=False)

        # Verificar si el jugador tiene una alianza y agregarla al mensaje embed si es el caso
        if alliance_name:
            embed.add_field(name="Alliance", value=alliance_name, inline=False)

        # Enviar el mensaje embed
        await ctx.send(embed=embed)
    else:
        await ctx.send("No se encontraron resultados para el término de búsqueda.")
# comando de las frases
frases = {
    1: "cuando tus ojos me miran...",
    2: "Voy a callear de concedes",
    3: "Sabes las temporadas de albion que te faltan",
    4: "Sos medio obsiso...",
    5: "10 millones es igual a un 1kg de milanesas",
    6: "argha decime que te parece...",
    7: "Tengo la compo definitiva!",
    8: "Dejame de molestar o te doy un beso...",
    9: "Comprame 10lts de perfumina",
    10: "Extraño a norganon",
    # Agrega más frases
}
@bot.command()
async def arg(ctx):
    random_frase = random.choice(list(frases.values()))
    await ctx.send(random_frase)

frases2 = {
    1: "Dale! no seas de lanus!",
    2: "Hoy juega el taladro, el sur esta de fiesta...",
    3: "Muchas gracias falcioni",
    4: "Piatnitzkysauruses un género de dinosaurio terópodo tetanuro que vivió hace aproximadamente 179 a 177 millones de años durante la parte baja del Período Jurásico en lo que hoy es Argentina.",
    5: "los mejores dias siempre fueron falcionistas",
    6: "https://www.youtube.com/watch?v=EicTgLehJX8",
    7: "El Piatnitzkysaurus  mide entre 4 y 5 metros de largo y llegando a pesar 275 kilogramos.",
    8: "https://tenor.com/view/cab-banfield-ban-clun-atletico-banfield-el-taladro-gif-14758214",
    
}
@bot.command()
async def harfen(ctx):
    random_frase2 = random.choice(list(frases2.values()))
    await ctx.send(random_frase2)
frases3 = {
    1: "Somos 5 esa blob t4 es peleable",
    2: "pasaron cosas...",
    3: "no se bro, no rompas las bolas",
    4: "me mori en el primer engage",
}
@bot.command()
async def cheddar(ctx):
    random_frase3 = random.choice(list(frases3.values()))
    await ctx.send(random_frase3)
# Define una función para crear un mensaje embed para los datos de la blacklist
def create_embed(data):
    embed = discord.Embed(title="Datos de la Blacklist", color=discord.Color.red())
    embed.add_field(name="Nombre", value=data[1], inline=False)
    embed.add_field(name="Motivo", value=data[2], inline=False)
    embed.add_field(name="Fecha", value=data[3], inline=False)
    embed.add_field(name="Oficial", value=data[4], inline=False)
    return embed

#comando para agregar datos a la tabla blacklist
@bot.command()
async def bl(ctx, nombre: str, *, motivo: str):
    if "<@&667310769162944532>" not in [f"<@&{rol.id}>" for rol in ctx.author.roles]:
        await ctx.send("No tienes los permisos necesarios para utilizar este comando.")
        return
    
    fecha = datetime.now().strftime("%Y-%m-%d")
    oficial = ctx.author.display_name
    
    connection = await aiomysql.connect(
			host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            autocommit=True
    )
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO blacklist (nombre, motivo, fecha, oficial) 
            VALUES (%s, %s, %s, %s)
            """,
            (nombre, motivo, fecha, oficial)
        )
        await ctx.send(f"Los datos de {nombre} han sido agregados a la blacklist.")

#comando para verificar si una persona está en la tabla blacklist
@bot.command()
async def check(ctx, nombre: str):
    connection = await aiomysql.connect(
			host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            autocommit=True
    )
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            SELECT * FROM blacklist WHERE nombre = %s
            """,
            (nombre,)
        )
        data = await cursor.fetchone()

        if data:
            await ctx.send(embed=create_embed(data))
        else:
            await ctx.send(f"{nombre} no está en la blacklist.")

    connection.close()

#comando para eliminar a una persona de la tabla blacklist
@bot.command()
async def desblacklist(ctx, nombre: str):
    if "<@&667310769162944532>" not in [f"<@&{rol.id}>" for rol in ctx.author.roles]:
        await ctx.send("No tienes los permisos necesarios para utilizar este comando.")
        return
    
    connection = await aiomysql.connect(
			host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
            autocommit=True
    )
    async with connection.cursor() as cursor:
        await cursor.execute(
            """
            DELETE FROM blacklist WHERE nombre = %s
            """,
            (nombre,)
        )
        if cursor.rowcount > 0:
            await ctx.send(f"{nombre} ha sido eliminado de la blacklist.")
        else:
            await ctx.send(f"{nombre} no estaba en la blacklist.")

    connection.close()

# Inicia el bot 
bot.run('tokendetubotxxxxxxxxxxxxxxxxxxxxxxxxxxx')
