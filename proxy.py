import asyncio
import urllib.request

async def forward(reader, writer):
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except Exception as e:
        print(f"Erro no forward: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def handle_client(reader, writer):
    try:
        data = await reader.read(4096)
        if not data:
            writer.close()
            await writer.wait_closed()
            return

        request_line = data.decode(errors='ignore').split('\n')[0]
        print(f"Requisição: {request_line.strip()}")

        if not request_line.strip():
            writer.close()
            await writer.wait_closed()
            return

        parts = request_line.strip().split()
        if len(parts) < 3:
            writer.close()
            await writer.wait_closed()
            return

        method, path, version = parts

        if method == 'GET' and path == '/':
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/html\r\n"
                "Connection: close\r\n\r\n"
                "<html><body><h1>PROXY SERVER!</h1></body></html>"
            )
            writer.write(response.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
            return

        if method == 'CONNECT':
            host, port = path.split(':')
            port = int(port)
        else:
            host = None
            for line in data.decode(errors='ignore').split('\r\n'):
                if line.lower().startswith("host:"):
                    host = line.split(":")[1].strip()
                    break
            port = 80

        if not host:
            print("Host não encontrado.")
            writer.close()
            await writer.wait_closed()
            return

        print(f"Conectando a {host}:{port}")
        try:
            remote_reader, remote_writer = await asyncio.open_connection(host, port)
        except Exception as e:
            print(f"Erro ao conectar ao host remoto: {e}")
            writer.close()
            await writer.wait_closed()
            return

        if method == "CONNECT":
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
        else:
            remote_writer.write(data)
            await remote_writer.drain()

        await asyncio.gather(
            forward(reader, remote_writer),
            forward(remote_reader, writer)
        )

    except Exception as e:
        print(f"Erro geral: {e}")
        writer.close()
        await writer.wait_closed()

def get_external_ip():
    try:
        with urllib.request.urlopen("https://api.ipify.org") as response:
            return response.read().decode()
    except Exception as e:
        return f"Erro ao obter IP externo: {e}"

async def main():
    external_ip = get_external_ip()
    print(f"Proxy async rodando na porta 7860...")
    print(f"IP externo (visível na internet): {external_ip}")

    server = await asyncio.start_server(handle_client, '0.0.0.0', 7860)

    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    asyncio.run(main())
