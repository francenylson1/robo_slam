import sqlite3
import json
from src.core.config import DATABASE_PATH, MAP_WIDTH, MAP_HEIGHT
import os
from typing import List, Tuple, Optional, Dict

class MapManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.conn = None
        self.cursor = None
        self._ensure_data_directory_exists()
        self._connect_db()
        self._create_tables()

    def _ensure_data_directory_exists(self):
        """Cria o diretório 'data' se ele não existir."""
        data_dir = os.path.dirname(self.db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"Diretório de dados criado: {data_dir}")

    def _connect_db(self):
        """Conecta ao banco de dados SQLite."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.cursor = self.conn.cursor()
            print(f"Conectado ao banco de dados: {self.db_path}")
        except sqlite3.Error as e:
            print(f"Erro ao conectar ao banco de dados: {e}")

    def _create_tables(self):
        """Cria as tabelas necessárias no banco de dados."""
        if not self.conn:
            print("Erro: Conexão com o banco de dados não estabelecida.")
            return
        try:
            # Tabela mapas
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS mapas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    largura REAL NOT NULL,
                    comprimento REAL NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 0
                )
            """)
            # Tabela pontos_interesse
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pontos_interesse (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapa_id INTEGER NOT NULL,
                    nome TEXT NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    tipo TEXT,
                    raio REAL,
                    FOREIGN KEY (mapa_id) REFERENCES mapas(id) ON DELETE CASCADE
                )
            """)
            # Tabela areas_proibidas
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS areas_proibidas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mapa_id INTEGER NOT NULL,
                    nome TEXT,
                    coordenadas TEXT NOT NULL,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    motivo TEXT,
                    FOREIGN KEY (mapa_id) REFERENCES mapas(id) ON DELETE CASCADE
                )
            """)
            self.conn.commit()
            print("Tabelas verificadas/criadas com sucesso.")
        except sqlite3.Error as e:
            print(f"Erro ao criar tabelas: {e}")

    def save_map(self, map_name: str, points_of_interest: dict, forbidden_areas: list):
        """
        Salva o mapa atual no banco de dados.
        Atualiza um mapa existente ou cria um novo.
        """
        if not self.conn:
            print("Erro: Conexão com o banco de dados não estabelecida.")
            return
        try:
            self.cursor.execute("SELECT id FROM mapas WHERE nome = ?", (map_name,))
            map_id = self.cursor.fetchone()

            if map_id:
                map_id = map_id[0]
                # Atualiza o mapa existente, desativa outros e define este como ativo
                self.cursor.execute("UPDATE mapas SET ativo = 0")
                self.cursor.execute("UPDATE mapas SET largura = ?, comprimento = ?, ativo = 1 WHERE id = ?",
                                    (MAP_WIDTH, MAP_HEIGHT, map_id))
                # Limpa pontos de interesse e áreas proibidas antigas
                self.cursor.execute("DELETE FROM pontos_interesse WHERE mapa_id = ?", (map_id,))
                self.cursor.execute("DELETE FROM areas_proibidas WHERE mapa_id = ?", (map_id,))
                print(f"Mapa '{map_name}' atualizado.")
            else:
                # Insere novo mapa e o define como ativo, desativando outros
                self.cursor.execute("UPDATE mapas SET ativo = 0")
                self.cursor.execute("INSERT INTO mapas (nome, largura, comprimento, ativo) VALUES (?, ?, ?, 1)",
                                    (map_name, MAP_WIDTH, MAP_HEIGHT))
                map_id = self.cursor.lastrowid
                print(f"Novo mapa '{map_name}' criado.")

            # Insere pontos de interesse
            for name, position in points_of_interest.items():
                self.cursor.execute("INSERT INTO pontos_interesse (mapa_id, nome, x, y, tipo) VALUES (?, ?, ?, ?, ?)",
                                    (map_id, name, position[0], position[1], "Mesa")) # Tipo fixo por enquanto

            # Insere áreas proibidas
            for area in forbidden_areas:
                # Converte lista de tuplas para string JSON
                coords_json = json.dumps(area)
                self.cursor.execute("INSERT INTO areas_proibidas (mapa_id, coordenadas) VALUES (?, ?)",
                                    (map_id, coords_json))

            self.conn.commit()
            print("Dados do mapa salvos com sucesso.")
        except sqlite3.Error as e:
            print(f"Erro ao salvar mapa: {e}")
            self.conn.rollback()

    def load_active_map(self) -> tuple[dict, list, str]:
        """
        Carrega o mapa ativo do banco de dados.
        Retorna (points_of_interest, forbidden_areas, map_name).
        """
        if not self.conn:
            print("Erro: Conexão com o banco de dados não estabelecida.")
            return {}, [], ""

        points_of_interest = {}
        forbidden_areas = []
        map_name = ""
        try:
            self.cursor.execute("SELECT id, nome FROM mapas WHERE ativo = 1")
            active_map = self.cursor.fetchone()

            if active_map:
                map_id, map_name = active_map
                print(f"Carregando mapa ativo: '{map_name}'")

                # Carrega pontos de interesse
                self.cursor.execute("SELECT nome, x, y FROM pontos_interesse WHERE mapa_id = ?", (map_id,))
                for row in self.cursor.fetchall():
                    points_of_interest[row[0]] = (row[1], row[2])

                # Carrega áreas proibidas
                self.cursor.execute("SELECT coordenadas FROM areas_proibidas WHERE mapa_id = ?", (map_id,))
                for row in self.cursor.fetchall():
                    coords_json = row[0]
                    forbidden_areas.append(json.loads(coords_json))

            else:
                print("Nenhum mapa ativo encontrado. Iniciando com mapa vazio.")

        except sqlite3.Error as e:
            print(f"Erro ao carregar mapa: {e}")

        return points_of_interest, forbidden_areas, map_name

    def get_all_map_names(self) -> list[str]:
        """
        Retorna uma lista com os nomes de todos os mapas salvos.
        """
        if not self.conn:
            print("Erro: Conexão com o banco de dados não estabelecida.")
            return []
        try:
            self.cursor.execute("SELECT nome FROM mapas ORDER BY nome")
            return [row[0] for row in self.cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Erro ao listar mapas: {e}")
            return []

    def load_map_by_name(self, map_name: str) -> tuple[dict, list, str]:
        """
        Carrega um mapa específico pelo nome e o define como ativo.
        Retorna (points_of_interest, forbidden_areas, map_name).
        """
        if not self.conn:
            print("Erro: Conexão com o banco de dados não estabelecida.")
            return {}, [], ""

        points_of_interest = {}
        forbidden_areas = []
        loaded_map_name = ""
        try:
            # Desativa todos os mapas e ativa o selecionado
            self.cursor.execute("UPDATE mapas SET ativo = 0")
            self.cursor.execute("UPDATE mapas SET ativo = 1 WHERE nome = ?", (map_name,))
            self.conn.commit()

            # Agora carrega o mapa recém-ativado
            return self.load_active_map()

        except sqlite3.Error as e:
            print(f"Erro ao carregar mapa por nome: {e}")
            self.conn.rollback()
        return {}, [], ""

    def close(self):
        """Fecha a conexão com o banco de dados."""
        if self.conn:
            self.conn.close()
            print("Conexão com o banco de dados fechada.")

    def get_forbidden_areas(self, map_id: int) -> List[List[Tuple[float, float]]]:
        """Obtém todas as áreas proibidas de um mapa"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT coordenadas FROM areas_proibidas 
                    WHERE mapa_id = ? AND ativo = 1
                """, (map_id,))
                areas = []
                for row in cursor.fetchall():
                    # Converte a string de coordenadas em lista de tuplas
                    coords_str = row[0]
                    coords_list = eval(coords_str)  # Converte string para lista
                    areas.append([(float(x), float(y)) for x, y in coords_list])
                return areas
        except Exception as e:
            print(f"Erro ao obter áreas proibidas: {e}")
            return []

    def get_active_map(self) -> Optional[Dict]:
        """Obtém o mapa ativo do banco de dados"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, nome, largura, comprimento 
                    FROM mapas 
                    WHERE ativo = 1
                """)
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'nome': row[1],
                        'largura': row[2],
                        'comprimento': row[3]
                    }
                return None
        except Exception as e:
            print(f"Erro ao obter mapa ativo: {e}")
            return None 