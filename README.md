# Memcached Distributed Cache Simulator - TP 01

¡Bienvenido al código para tu **Trabajo Práctico 01 de Sistemas Distribuidos**!

Este proyecto demuestra cómo un clúster de Memcached maneja la carga de una aplicación y, lo más importante, qué ocurre cuando un nodo del clúster se cae abruptamente, utilizando el concepto clave de **Consistent Hashing** (Hashing Consistente).

## 🚀 Cómo ejecutarlo

Asegúrate de tener **Docker** y **Docker Compose** instalados en la máquina (o VM en la nube) donde harás la demostración.

1. Abre una terminal y levanta el clúster (compuesto por 3 nodos de Memcached y 1 aplicación Python):
   ```bash
   docker-compose up --build
   ```

2. Verás en los logs cómo la aplicación Python (`cache-simulator`) empieza a pedir perfiles de usuario de forma continua y aleatoria.
   - 🟪 **[MISS]**: La primera vez que pide un perfil, no está en caché. Simula ir a la Base de Datos (tarda 1.5s).
   - 🟦 **[SET]**: Guarda el dato en Memcached.
   - 🟩 **[HIT]**: La siguiente vez que pida el mismo usuario, lo sacará de Memcached instantáneamente (0.00x segundos).

## 💥 Cómo demostrar Tolerancia a Fallos (El Crash Test)

Para obtener la nota máxima y responder a la rúbrica del profesor ("¿qué ocurre si una máquina se cae abruptamente?"), haz lo siguiente durante tu presentación:

1. Deja corriendo la primera terminal con `docker-compose up`. Ya deberías estar viendo puros **[HIT]** porque todos los usuarios están cacheados.
2. Abre **otra terminal** y mata uno de los nodos de Memcached de forma abrupta (simulando que el servidor físico o la VM se apagó/quemó):
   ```bash
   docker stop memcached-2
   ```
3. **Vuelve a la primera terminal y observa los logs de la aplicación:**
   - Notarás que **algunos** usuarios empiezan a dar **[MISS]**. Estos son exclusivamente los usuarios cuyas llaves estaban asignadas a `memcached-2`.
   - Sin embargo, **otros usuarios seguirán dando [HIT]** ininterrumpidamente.
   - **¡Esto demuestra el Consistent Hashing en acción!** Si usáramos hashing tradicional, al caer un nodo toda la caché se invalidaría y tu base de datos colapsaría por la avalancha de peticiones. Con Consistent Hashing, solo perdemos (1/N) de los datos, y el sistema distribuido sobrevive.
   - La aplicación detectará el Miss de los datos perdidos, irá a la DB, y volverá a guardar esos perfiles perdidos redistribuyéndolos en los nodos que quedan vivos (`memcached-1` o `memcached-3`).

## 🧠 Puntos Clave para tu Presentación (Guion Sugerido)

Durante los 5 minutos que tienes para hablar del framework, te sugiero mencionar estos conceptos:

1. **¿Qué es Memcached?**: Es un almacén de valores-clave (key-value store) en memoria de ultra alto rendimiento, diseñado para escalar sistemas distribuidos aliviando la carga de lectura de la base de datos.
2. **Nuestra Arquitectura**: Usamos el patrón **Cache-Aside**. La aplicación (Python) primero revisa la caché. Si no está (Miss), va a la DB y ella misma actualiza la caché. Memcached no habla con la DB, es un sistema "tonto" pero rapidísimo.
3. **El desafío del Hashing Tradicional vs Consistente**:
   - En esta demo usamos la librería `pymemcache` configurada con un `HashClient`. Esto forma un "anillo" virtual de servidores. 
   - Si agregas o quitas un servidor, solo se reasignan las llaves cercanas a ese servidor en el anillo. Evita el temido *"Cache Stampede"*.
4. **Tolerancia a fallos**: Memcached por diseño *no* replica datos nativamente entre nodos (a diferencia de Redis o Cassandra). Por lo tanto, la tolerancia a fallos y la distribución inteligente del tráfico es responsabilidad del **Cliente** (nuestro script Python), que sabe a qué nodo ir y sobrevive a caídas de conexión sin colapsar.
