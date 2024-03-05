# ST0263 Tópicos Especiales en Telemática

## Estudiante:

- Sebastian Velez Galeano, svelezg4@eafit.edu.co

## Profesor:

- Alvaro Enrique Ospina Sanjuan, aeospinas@eafit.edu.co

# P2P - Comunicación entre procesos mediante API REST y RPC

## 1. Descripción

Este proyecto implementa un sistema Peer-to-Peer (P2P) para la transperencia de archivos, se esta utilizando un esquema de red no estructurada, esta esta basada en servidor de directorio y localización. Cada nodo en la red (peer) actúa como cliente y servidor a la vez, esto permite consultas sobre los recursos disponibles realizando transferencia de archivos (simulados).

### **1.1. Aspectos cumplidos**

- #### **Microservicios y Conexiones Simultáneas:**

  Se implementaron microservicios tanto en el servidor como en los peers, permitiendo múltiples conexiones y operaciones concurrentes.

- #### **Registro y Gestión de Peers:**

  Los peers se registran en el sistema a través del servidor, que maneja el inicio y cierre de sesión, así como su estado up o down por medio de **(heartbeats)** para mantener actualizado el estado de los peers.

- #### **Descubrimiento de Archivos:**

  Los peers pueden listar y descubrir archivos disponibles en la red mediante consultas al servidor centralizado, que mantiene un índice de los archivos compartidos por cada peer.

- #### **Simulación de Transferencia de Archivos:**

  Aunque no se realiza la transferencia real de archivos, se simula esta funcionalidad a través de servicios que permiten a los peers 'subir' información sobre archivos y 'descubrir' archivos disponibles en otros peers.

- #### **Uso de gRPC y REST API:**
  Para las comunicaciones, se emplea gRPC en los microservicios de los peers, permitiendo operaciones como listar archivos y descubrir archivos en otros peers, y apiREST en el servidor central para la gestión de peers y archivos.

### **1.2. Aspectos no cumplidos**

- ### **Transferencia Real de Archivos entre Peers:**

  La transferencia de archivos físicos entre peers no se implementó, actualmente solo se **simula** mediante el intercambio de información sobre los archivos de peer a peer.

- ### **Implementación de MOM (Middleware Orientado a Mensajes):**

  No se integró un sistema **MOM** para mejorar la comunicación entre componentes.

- ### **Despliegue en AWS:**
  El sistema se desplego y se probo local con **Docker** no se realizo el despliegue en **AWS**.

## 2. Información general

- El **Server.py** utiliza **Flask** para gestionar la lógica de servidor, sirve para autenticación de usuarios, el registro y monitoreo de los peers activos a través de heartbeats, usa una base de datos para almacenar la información de cada peer como: URL y puerto del peer, el estado y los archivos que cada peer tiene.

- Los peers se componen en **Pclient.py** y **Pserver.py**, operan como clientes y servidores. **Pclient.py** maneja la interfaz de usuario para interactuar con la red, mientras que **Pserver.py** atiende solicitudes de otros peers usando **gRPC**.

- La arquitectura emplea **SQLite** para almacenar información relevante tambien se usa **flask** internamente por parte del server y **concurrent.futures** port parte del cleinte (peer) para la gestión de tareas concurrentes.

## 3. Ambiente de desarrollo

#### Este proyecto se desarrolló utilizando Python **3.8** y Docker **25.0.3**.

#### **Librerías principales:**

- **Flask 3.0.2:** Utilizada para implementar la API REST en el servidor.
- **grpcio grpcio-tools 1.62.0:** Utilizada para la comunicación entre peers.
- **SQLAlchemy 2.0.27:** Utilizada para la persistencia de datos, almacenando información sobre los peers.
- **Concurrent.futures:** Utilizada para manejar la concurrencia.

#### **Librerías secundarias:**

- **os**
- **logging**
- **requests 2.31.0**
- **json**
- **datetime**
- **dotenv**
- **subprocess**

#### **Docker**

- Usamos Docker para realizar contenedores con el **Servidor** y los **Peers**.

- #### **Dockerfiles:**

  - **Servidor:** Se creó un **Dockerfile** para construir la imagen del servidor, instalando todas las dependencias necesarias y configurando el entorno de ejecución para el servicio de servidor P2P.

  - **Peers:** Cada peer tiene su **Dockerfile** que prepara el entorno necesario para su funcionamiento, para que cada peer pueda operar de manera independiente dentro de su propio contenedor.

- #### **Docker Compose:**
  - Utilizamos **docker-compose.yml** para definir y gestionar la configuración de los múltiples contenedores (servidor y 3 peers), asignando puertos específicos a cada uno para evitar conflictos y facilitar la comunicación entre ellos.

## 4. Ambiente de ejecución

#### Simulamos un entorno de producción utilizando contenedores Docker.

- ### Configuración de contenedores

  #### El archivo docker-compose.yml incluye los siguientes servicios:

  - **Servidor:** Configura el contenedor que ejecuta el **servidor** del sistema P2P, especificando el puerto de escucha y las variables de entorno.

  - **Peers:** Define tres contenedores para los **peers**, asignando a cada uno un puerto único y estableciendo las variables de entorno requeridas para la **comunicación con el servidor y entre peers**.

- ### Configuración de los Parámetros

  - **Servidor:** El servicio **server** utiliza la imagen construida a partir del directorio **./server**. Se expone el puerto **4001** tanto internamente como externamente, esto nos permite la comunicación con el servidor. Las variables de entorno **SERVER_URL** y **SERVER_PORT** se establecen para definir la URL del servidor y el puerto en el que escucha.

  - **Peers:** Cada peer **(peer1, peer2, peer3)** tiene su propia configuración. Se construyen a partir del directorio **./peer** y exponen puertos únicos **(5001 para peer1, 5002 para peer2, y 5003 para peer3)** para evitar conflictos de red. Las variables **SERVER_URL** y **SERVER_PORT** son para conectarse al servidor, y las variables **GRPC_URL** y **GRPC_PORT** definen la URL y el puerto para la comunicación gRPC entre peers.

- ### Instrucciones de ejecución

  - **Construcción de contenedores:** Utiliza el comando

    ```
    docker-compose up -d --build
    ```

    para construir e iniciar los contenedores definidos en **docker-compose.yml**. Este comando también descarga las imágenes base y las dependencias necesarias.

  - **Acceso a los contenedores:** Para interactuar con un peer específico se utiliza el comando:

    ```
    docker exec -it <nombre-del-contenedor> /bin/bash
    ```

    Ejemplo para ingresar a la consola del peer 1:

    ```
    docker exec -it 337b9bb9d7d6 /bin/bash
    ```

    para acceder a la terminal del contenedor (peer).

  - **Ejecución de scripts:** Dentro del contenedor (peer), se puede ejecutar el archivo de p2p.py con el siguente comando:

    ```
    python p2p.py
    ```

    este comando inicia el proceso del peer, este inicia pserver.py y pclient.py. Esto permite al peer funcionar simultáneamente como cliente y servidor dentro de la red P2P.

- ### interaccion del peer

  - #### **Inicio de Sesión:**

    Se le pide a el usuario que ingrese su username y password para autenticarse en el sistema.

    ```
    ...Login to your account...
    Enter username:
    Enter password:
    ```

    Usuarios Autenticados Actualmente:

    - **Peer1 -**
      Username: **1**
      Password: **1**
    - **Peer2 -**
      Username: **2**
      Password: **2**
    - **Peer3 -**
      Username: **3**
      Password: **3**

  - #### **Selección de Conexión:**

    El usuario elige si desea conectarse al servidor o directamente a otro peer.

    ```
    Connect to Server or Peer?
    1. Server
    2. Peer
    Connect to (1) Server or (2) Peer?:
    ```

    - **Opción 1:** Conectarse al **servidor** para gestionar archivos y obtener información sobre los peers activos. **(mas usado para testing)**
    - **Opción 2:** Conectarse **directamente a otro peer** para todas las interacciones P2P, como la descarga o listar archivos por medio de otro peer.

  - #### **Interacción con el Servidor (si se conectar al servidor):**

    - **Subir un Archivo:** El usuario puede subir la **información** de un archivo, incluyendo su **nombre** y **URL**. (solo dummy, no sube archivos reales, solo le dice al servidor que que tiene un archivo local nuevo para ser descargado por otro peer)
    - **Listar Peers Activos:** Se puede solicitar una lista de todos los peers activos en la red, esta lista contiene detalles como el nombre de usuario y la URL de gRPC.
    - **Listar Archivos Disponibles:** Se puede pedir una lista de todos los archivos disponibles en la red, esta lista contiene detalles como el nombre y URL del archivo y la cantidad de peers que lo tienen.
    - **Cambiar conexión:** Se utiliza para cambiar la conexión del peer. Si está conectado al servidor, puede cambiarse y conectarse a un peer.

    ```
    ...|  Connected as: 1  |...
    ...|  To server  |...
    ...|  localhost:4001  |...
    Options:
    1. Upload a file
    2. List active peers
    3. List all available files
    4. Change connection
    5. Exit
    ```

  - Interacción Directa con Peers (si se conectar a un peer):

    - **Listar Archivos del Peer:** Se puede solicitar un listado de los archivos disponibles, esto lista todos los archivos disponibles de todos los peers activos.
    - **Descargar Archivo del Peer:** El usuario puede solicitar la "descarga" de un archivo desde el peer conectado. Esta acción simula la transferencia de archivos recuperando la información del archivo del peer, i simulando su transferencia desde el peer que tiene la informacion, no del servidor.
    - **Subir un Archivo:** El mismo metodo para subir un archivo al server. (solo dummy, no sube archivos reales, solo le dice al servidor que que tiene un archivo local nuevo para ser descargado por otro peer)
    - **Cambiar conexión:** Se utiliza para cambiar la conexión del peer. (Igual a la intereaccion con el server)

    ```
    ...| Connected as: 1 |...
    ...| To Peer: 2 |...
    ...| localhost:5002 |...
    Peer Options:\n
    1. List files from peer
    2. Download file from peer
    3. Upload a file
    4. Change connection
    5. Exit
    ```

## 5. Referencias:

- Flask: https://flask.palletsprojects.com/es/main/quickstart/
- Docker Compose: https://docs.docker.com/compose/
- Docker: https://www.docker.com/blog/how-to-dockerize-your-python-applications/
- gRPC: https://grpc.io/docs/languages/python/basics/
- gRPC: https://grpc.io/docs/languages/python/quickstart/
- gRPC: https://www.velotio.com/engineering-blog/grpc-implementation-using-python
- youtube: https://www.youtube.com/watch?v=WB37L7PjI5k&t=967s
- youtube: https://www.youtube.com/watch?v=E0CaocyNYKg
