import math
import os
import random
import sys
import pygame
from collections import deque
from board import boards


pygame.init()


def bfs(grid, start, end):
    rows, cols = len(grid), len(grid[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    queue = deque([(start[0], start[1], [])])
    visited = set()
    visited.add((start[0], start[1]))

    while queue:
        x, y, path = queue.popleft()
        if (x, y) == end:
            return path
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if ny < 0:
                ny = cols - 1
            elif ny >= cols:
                ny = 0

            if 0 <= nx < rows and (nx, ny) not in visited:
                if grid[nx][ny] < 3 or grid[nx][ny] == 9:
                    queue.append((nx, ny, path + [(nx, ny)]))
                    visited.add((nx, ny))
    print("no path is founded")
    return []


def draw_path(path, screen, x_grid, y_grid):
    if path:
        for row, col in path:
            x = col * x_grid + x_grid // 2
            y = row * y_grid + y_grid // 2
            pygame.draw.circle(screen, (255, 0, 0), (x, y), 4)


class Pacman:
    def __init__(self, game, speed=2):
        self.game = game
        self.speed = speed
        self.direction = 0
        self.collision_state = False
        self.counter = 0
        self.x = 0
        self.y = 0
        self.reset()

    def reset(self):
        self.direction = 0
        self.collision_state = False
        self.x = self.game.pacman_home_x[self.game.current_map]
        self.y = self.game.pacman_home_y[self.game.current_map]
        self.counter = 0

    def check_collision(self, new_x, new_y):
        y_grid = ((self.game.height - 50) // 32)
        x_grid = (self.game.width // 30)
        row = int((new_y + 40) // y_grid)
        col = int((new_x + 40) // x_grid)
        if col <= 0 or col >= 30:
            return False
        return self.game.level[row][col] >= 3

    def move(self):
        y_grid = ((self.game.height - 50) // 32)
        x_grid = (self.game.width // 30)
        new_x, new_y = self.x, self.y

        if not self.collision_state:
            if self.direction == 0:
                new_x += self.speed
            elif self.direction == 1:
                new_x -= self.speed
            elif self.direction == 2:
                new_y -= self.speed
            elif self.direction == 3:
                new_y += self.speed

            if self.check_collision(new_x, new_y):
                self.collision_state = True
            else:
                self.x, self.y = new_x, new_y
                row = int((self.y + 40) // y_grid)
                col = int((self.x + 40) // x_grid)

                if self.x + 40 <= 0:
                    self.x = self.game.width - 10 - 40
                    col = int((self.x + 40) // x_grid)
                    for ghost in self.game.ghosts:
                        ghost.bfs_counter = ghost.bfs_interval
                        ghost.move()
                elif self.x + 40 >= self.game.width:
                    self.x = 10 - 40
                    col = int((self.x + 40) // x_grid)
                    for ghost in self.game.ghosts:
                        ghost.bfs_counter = ghost.bfs_interval
                        ghost.move()

                if 0 <= row < len(self.game.level) and 0 <= col < len(self.game.level[0]):
                    if self.game.level[row][col] == 1:
                        self.game.score += 10
                        self.game.level[row][col] = 0
                        self.game.dots_eaten_tracker += 1
                    elif self.game.level[row][col] == 2:
                        self.game.score += 50
                        self.game.total_pellets += 5
                        self.game.level[row][col] = 0
                        for ghost in self.game.ghosts:
                            ghost.sober = False
                        self.game.chase_mode = True
                        self.game.chase_counter = 0

    def draw(self):
        if self.collision_state:
            image = self.game.collision_image
        else:
            image = self.game.pacman_images[self.counter // 5 % len(self.game.pacman_images)]

        if self.direction == 0:
            self.game.screen.blit(image, (self.x, self.y))
        elif self.direction == 1:
            self.game.screen.blit(pygame.transform.flip(image, True, False), (self.x, self.y))
        elif self.direction == 2:
            self.game.screen.blit(pygame.transform.rotate(image, 90), (self.x, self.y))
        elif self.direction == 3:
            self.game.screen.blit(pygame.transform.rotate(image, -90), (self.x, self.y))

        self.counter += 1


class Ghost:
    def __init__(self, game, x, y, image, speed, in_box=True, name="ghost"):
        self.game = game
        self.x = x
        self.y = y
        self.image = image
        self.normal_image = image
        self.speed = speed
        self.direction = 0
        self.in_box = in_box
        self.name = name
        self.path = []
        self.path_index = 0
        self.bfs_interval = 10
        self.bfs_counter = 0
        self.chase_image = self.game.ghost_images["chase"]
        self.dead_image = self.game.ghost_images["dead"]
        self.is_dead = False
        self.sober = False
        self.cooldown_timer = 20
        self.teleport_cooldown_timer = 30
        self.revive_timer = 0

    def _grid_pos(self):
        y_grid = ((self.game.height - 50) // 32)
        x_grid = (self.game.width // 30)
        row = int((self.y + 30) // y_grid)
        col = int((self.x + 30) // x_grid)
        return row, col, x_grid, y_grid

    def update_path(self):
        row, col, x_grid, y_grid = self._grid_pos()
        pacman_row = int((self.game.pacman.y + 40) // y_grid)
        pacman_col = int((self.game.pacman.x + 40) // x_grid)

        if self.name == "blinky":
            if self.is_dead:
                self.path = bfs(self.game.level, (row, col), ((self.game.pinky_home_y[self.game.current_map] + 30) // y_grid, (self.game.pinky_home_x[self.game.current_map] + 30) // x_grid))
            else:
                self.path = bfs(self.game.level, (row, col), (pacman_row, pacman_col))
                self.game.blinky_x = self.x
                self.game.blinky_y = self.y

        elif self.name == "pinky":
            if self.is_dead:
                self.path = bfs(self.game.level, (row, col), ((self.game.pinky_home_y[self.game.current_map] + 30) // y_grid, (self.game.pinky_home_x[self.game.current_map] + 30) // x_grid))
            else:
                target_pacman_row = int((self.game.pacman.y + 40) // y_grid)
                target_pacman_col = int((self.game.pacman.x + 40) // x_grid)

                if self.cooldown_timer < self.game.chase_switch_timer:
                    pass
                elif (math.pow(col - target_pacman_col, 2) + math.pow(row - target_pacman_row, 2)) <= 16:
                    self.cooldown_timer = 0
                    self.path = bfs(self.game.level, (row, col), (target_pacman_row, target_pacman_col))
                else:
                    self.cooldown_timer = 0
                    prediction_steps = 4
                    predicted_row = target_pacman_row
                    predicted_col = target_pacman_col

                    if self.game.pacman.direction == 0:
                        predicted_col += prediction_steps
                    elif self.game.pacman.direction == 1:
                        predicted_col -= prediction_steps
                    elif self.game.pacman.direction == 2:
                        predicted_row -= prediction_steps
                    elif self.game.pacman.direction == 3:
                        predicted_row += prediction_steps

                    if 0 <= predicted_row < len(self.game.level) and 0 <= predicted_col < len(self.game.level[0]) and self.game.level[predicted_row][predicted_col] < 3:
                        self.path = bfs(self.game.level, (row, col), (predicted_row, predicted_col))
                    else:
                        found_valid_target = False
                        for steps in range(prediction_steps, -1, -1):
                            check_row, check_col = target_pacman_row, target_pacman_col
                            if self.game.pacman.direction == 0:
                                check_col += steps
                            elif self.game.pacman.direction == 1:
                                check_col -= steps
                            elif self.game.pacman.direction == 2:
                                check_row -= steps
                            elif self.game.pacman.direction == 3:
                                check_row += steps

                            if 0 <= check_row < len(self.game.level) and 0 <= check_col < len(self.game.level[0]) and self.game.level[check_row][check_col] < 3:
                                self.path = bfs(self.game.level, (row, col), (check_row, check_col))
                                found_valid_target = True
                                break

                        if not found_valid_target:
                            self.path = bfs(self.game.level, (row, col), (target_pacman_row, target_pacman_col))

        elif self.name == "clyde":
            if self.is_dead:
                self.path = bfs(self.game.level, (row, col), ((self.game.clyde_home_y[self.game.current_map] + 30) // y_grid, (self.game.clyde_home_x[self.game.current_map] + 30) // x_grid))
            else:
                if self.game.score >= 600:
                    if self.cooldown_timer < self.game.chase_switch_timer:
                        pass
                    elif (math.pow(col - pacman_col, 2) + math.pow(row - pacman_row, 2)) <= 64:
                        self.path = bfs(self.game.level, (row, col), (850 // x_grid, 80 // y_grid))
                    else:
                        self.path = bfs(self.game.level, (row, col), (pacman_row, pacman_col))

        elif self.name == "inky":
            if self.is_dead:
                self.path = bfs(self.game.level, (row, col), ((self.game.inky_home_y[self.game.current_map] + 30) // y_grid, (self.game.inky_home_x[self.game.current_map] + 30) // x_grid))
            else:
                if self.game.dots_eaten_tracker >= 30:
                    blinky_row = int((self.game.blinky_y + 30) // y_grid)
                    blinky_col = int((self.game.blinky_x + 30) // x_grid)
                    pacman_ahead_row, pacman_ahead_col = pacman_row, pacman_col

                    if self.game.pacman.direction == 0:
                        pacman_ahead_col += 2
                    elif self.game.pacman.direction == 1:
                        pacman_ahead_col -= 2
                    elif self.game.pacman.direction == 2:
                        pacman_ahead_row -= 2
                    elif self.game.pacman.direction == 3:
                        pacman_ahead_row += 2

                    target_row = pacman_ahead_row + (pacman_ahead_row - blinky_row)
                    target_col = pacman_ahead_col + (pacman_ahead_col - blinky_col)

                    found_path = False

                    if 0 <= target_row < len(self.game.level) and 0 <= target_col < len(self.game.level[0]):
                        if self.game.level[target_row][target_col] < 3:
                            self.path = bfs(self.game.level, (row, col), (target_row, target_col))
                            found_path = True
                        else:
                            search_radius = 1
                            while not found_path and search_radius < max(len(self.game.level), len(self.game.level[0])):
                                for i in range(-search_radius, search_radius + 1):
                                    for j in range(-search_radius, search_radius + 1):
                                        check_row, check_col = target_row + i, target_col + j
                                        if (i in {-search_radius, search_radius} or j in {-search_radius, search_radius}) and 0 <= check_row < len(self.game.level) and 0 <= check_col < len(self.game.level[0]) and self.game.level[check_row][check_col] < 3:
                                            self.path = bfs(self.game.level, (row, col), (check_row, check_col))
                                            found_path = True
                                            break
                                    if found_path:
                                        break
                                search_radius += 1
                    else:
                        if target_row < 0:
                            for r in range(0, row + 1):
                                if 0 <= r < len(self.game.level) and 0 <= target_col < len(self.game.level[0]) and self.game.level[r][target_col] < 3:
                                    self.path = bfs(self.game.level, (row, col), (r, target_col))
                                    found_path = True
                                    break
                        elif target_row >= len(self.game.level):
                            for r in range(len(self.game.level) - 1, row - 1, -1):
                                if 0 <= r < len(self.game.level) and 0 <= target_col < len(self.game.level[0]) and self.game.level[r][target_col] < 3:
                                    self.path = bfs(self.game.level, (row, col), (r, target_col))
                                    found_path = True
                                    break

                        if not found_path:
                            if target_col < 0:
                                for c in range(0, col + 1):
                                    if 0 <= target_row < len(self.game.level) and 0 <= c < len(self.game.level[0]) and self.game.level[target_row][c] < 3:
                                        self.path = bfs(self.game.level, (row, col), (target_row, c))
                                        found_path = True
                                        break
                            elif target_col >= len(self.game.level[0]):
                                for c in range(len(self.game.level[0]) - 1, col - 1, -1):
                                    if 0 <= target_row < len(self.game.level) and 0 <= c < len(self.game.level[0]) and self.game.level[target_row][c] < 3:
                                        self.path = bfs(self.game.level, (row, col), (target_row, c))
                                        found_path = True
                                        break

                    if not found_path:
                        self.path = bfs(self.game.level, (row, col), (pacman_row, pacman_col))

        self.path_index = 0

    def move(self):
        y_grid = ((self.game.height - 50) // 32)
        x_grid = (self.game.width // 30)

        self.bfs_counter += 1
        if self.bfs_counter >= self.bfs_interval:
            self.update_path()
            self.bfs_counter = 0

        if self.path:
            if self.path_index < len(self.path):
                self.in_box = False
                target_row, target_col = self.path[self.path_index]
                target_x = target_col * x_grid + x_grid // 2 - 30
                target_y = target_row * y_grid + y_grid // 2 - 30

                dx = target_x - self.x
                dy = target_y - self.y

                move_x = min(abs(dx), self.speed) * (1 if dx > 0 else -1 if dx < 0 else 0)
                move_y = min(abs(dy), self.speed) * (1 if dy > 0 else -1 if dy < 0 else 0)

                self.x += move_x
                self.y += move_y

                row = int((self.y + 30) // y_grid)
                col = int((self.x + 30) // x_grid)

                if self.game.level[row][col] == -1 and self.teleport_cooldown_timer >= 30:
                    if self.x + 30 <= x_grid // 2 + 10:
                        self.x = self.game.width - x_grid - 30
                        self.teleport_cooldown_timer = 0
                    elif self.x + 30 >= self.game.width - x_grid:
                        self.x = x_grid // 2 - 30
                        self.teleport_cooldown_timer = 0

                if abs(self.x - target_x) < 2 and abs(self.y - target_y) < 2:
                    self.path_index += 1
            else:
                self.path = []
                self.path_index = 0
        if self.is_dead:
            if self.name == "blinky":
                house_x = self.game.pinky_home_x[self.game.current_map]
                house_y = self.game.pinky_home_y[self.game.current_map]
            elif self.name == "pinky":
                house_x = self.game.pinky_home_x[self.game.current_map]
                house_y = self.game.pinky_home_y[self.game.current_map]
            elif self.name == "clyde":
                house_x = self.game.clyde_home_x[self.game.current_map]
                house_y = self.game.clyde_home_y[self.game.current_map]
            elif self.name == "inky":
                house_x = self.game.inky_home_x[self.game.current_map]
                house_y = self.game.inky_home_y[self.game.current_map]
            if abs(self.x - house_x) < 30 and abs(self.y - house_y) < 30:
                self.revive_timer += 1
                self.in_box = True
                if self.revive_timer >= 30:
                    self.is_dead = False
                    self.image = self.normal_image
                    self.sober = True
                    self.revive_timer = 0

    def chase_move(self):
        y_grid = ((self.game.height - 50) // 32)
        x_grid = (self.game.width // 30)
        row = int((self.y + 30) // y_grid)
        col = int((self.x + 30) // x_grid)

        if self.game.chase_mode and not self.is_dead and not self.sober and not self.in_box:
            if self.direction == 0 and self.game.level[row][col - 1] >= 3:
                can_move_forward = False
            elif self.direction == 1 and self.game.level[row][col + 1] >= 3:
                can_move_forward = False
            elif self.direction == 2 and self.game.level[row - 1][col] >= 3:
                can_move_forward = False
            elif self.direction == 3 and self.game.level[row + 1][col] >= 3:
                can_move_forward = False
            else:
                can_move_forward = True

            if can_move_forward:
                if self.direction == 0:
                    self.x -= self.speed - 0.5
                elif self.direction == 1:
                    self.x += self.speed - 0.5
                elif self.direction == 2:
                    self.y -= self.speed - 0.5
                elif self.direction == 3:
                    self.y += self.speed - 0.5
            else:
                possible_moves = []
                if self.game.level[row][col - 1] < 3 and self.direction != 1:
                    possible_moves.append(0)
                if self.game.level[row][col + 1] < 3 and self.direction != 0:
                    possible_moves.append(1)
                if self.game.level[row - 1][col] < 3 and self.direction != 3:
                    possible_moves.append(2)
                if self.game.level[row + 1][col] < 3 and self.direction != 2:
                    possible_moves.append(3)

                if possible_moves:
                    best_direction = -1
                    max_distance_sq = float("-inf")

                    for direction in possible_moves:
                        next_x, next_y = self.x, self.y
                        if direction == 0:
                            next_x -= x_grid
                        elif direction == 1:
                            next_x += x_grid
                        elif direction == 2:
                            next_y -= y_grid
                        elif direction == 3:
                            next_y += y_grid

                        distance_sq = pow(self.game.pacman.x - next_x, 2) + pow(self.game.pacman.y - next_y, 2)
                        if distance_sq > max_distance_sq:
                            max_distance_sq = distance_sq
                            best_direction = direction

                    if best_direction != -1:
                        self.direction = best_direction
                        if self.direction == 0:
                            self.x -= self.speed
                        elif self.direction == 1:
                            self.x += self.speed
                        elif self.direction == 2:
                            self.y -= self.speed
                        elif self.direction == 3:
                            self.y += self.speed
                else:
                    if self.direction == 0 and self.game.level[row][col - 1] < 3:
                        self.x -= self.speed
                    elif self.direction == 1 and self.game.level[row][col + 1] < 3:
                        self.x += self.speed
                    elif self.direction == 2 and self.game.level[row - 1][col] < 3:
                        self.y -= self.speed
                    elif self.direction == 3 and self.game.level[row + 1][col] < 3:
                        self.y += self.speed

    def draw(self):
        if self.game.chase_mode and not self.is_dead and not self.sober and not self.in_box:
            self.game.screen.blit(self.chase_image, (self.x, self.y))
        elif self.is_dead:
            self.game.screen.blit(self.dead_image, (self.x, self.y))
            self.move()
        else:
            self.game.screen.blit(self.image, (self.x, self.y))

    def reset_ghost(self):
        self.sober = False
        if self.name == "blinky":
            self.x = self.game.blinky_home_x[self.game.current_map]
            self.y = self.game.blinky_home_y[self.game.current_map]
        elif self.name == "inky":
            self.x = self.game.inky_home_x[self.game.current_map]
            self.y = self.game.inky_home_y[self.game.current_map]
            self.in_box = True
        elif self.name == "pinky":
            self.x = self.game.pinky_home_x[self.game.current_map]
            self.y = self.game.pinky_home_y[self.game.current_map]
            self.in_box = True
        elif self.name == "clyde":
            self.x = self.game.clyde_home_x[self.game.current_map]
            self.y = self.game.clyde_home_y[self.game.current_map]
            self.in_box = True

        if self.is_dead:
            self.is_dead = False
            self.image = self.normal_image


class Game:
    def __init__(self):
        self.width = 900
        self.height = 950
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.timer = pygame.time.Clock()
        self.fps = 60
        self.PI = math.pi

        self.asset_root = os.path.dirname(os.path.abspath(__file__))
        self.font_dir = os.path.abspath(os.path.join(self.asset_root, ".."))

        self.font = pygame.font.Font(None, 40)  # Use default pygame font
        self.chinese_font = self._load_font("chinesefont.ttf", 30)
        self.title_font = self._load_font("BoldChinese.ttf", 60)

        self.menu_options = ["開始遊玩", "遊戲簡介", "難度選擇", "離開"]
        self.selected_option = -1
        self.selected_map_index = -1
        self.selected_difficulty_index = -1

        self.current_map = 0
        self.level = [list(row) for row in boards[self.current_map]]

        self.pacman_home_x = [420, 420, 500]
        self.pacman_home_y = [650, 470, 320]

        self.blinky_home_x = [420, 420, 320]
        self.blinky_home_y = [320, 385, 320]

        self.pinky_home_x = [480, 420, 480]
        self.pinky_home_y = [400, 305, 400]

        self.inky_home_x = [420, 500, 420]
        self.inky_home_y = [400, 570, 400]

        self.clyde_home_x = [360, 360, 360]
        self.clyde_home_y = [400, 570, 400]

        self.pacman_images = []
        self.ghost_images = {}
        self.collision_image = None
        self.background_img = None
        self.map_preview_images = []

        self.player_speed = 2
        self.ghost_speed = 1.5
        self.chase_mode = False
        self.chase_counter = 0
        self.chase_switch_timer = 20
        self.chase_duration = 6 * self.fps

        self.game_over_alpha = 0
        self.game_over_text_alpha = 255

        self.score = 0
        self.full_health = 3
        self.lives = self.full_health
        self.pacman = Pacman(self, speed=self.player_speed)
        self.blinky_x = self.blinky_home_x[self.current_map]
        self.blinky_y = self.blinky_home_y[self.current_map]

        self.ghosts = []
        self.ghost_delay_counter = 60
        self.dots_eaten_tracker = 0
        self.total_pellets = 0

        self.victory_alpha = 0
        self.victory_text_alpha = 255
        self.final_score = 0

        self.game_state = "menu"

        self.load_images()
        self.reset_game()

    def _load_font(self, filename, size):
        path = os.path.join(self.font_dir, filename)
        return pygame.font.Font(path, size)

    def load_images(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        images_folder = os.path.join(script_dir, "images")

        self.pacman_images = [
            pygame.transform.scale(pygame.image.load(os.path.join(images_folder, f"pacman{i}.png")), (80, 80))
            for i in range(1, 5)
        ]
        self.collision_image = pygame.transform.scale(
            pygame.image.load(os.path.join(images_folder, "collision.png")), (80, 80)
        )

        self.ghost_images = {
            "blinky": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "red.png")), (60, 60)),
            "inky": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "inky.png")), (60, 60)),
            "pinky": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "pinky.png")), (60, 60)),
            "clyde": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "clyde.png")), (60, 60)),
            "chase": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "chase.png")), (60, 60)),
            "dead": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "dead.png")), (80, 80)),
        }

        self.map_preview_images = []
        for i in range(1, 4):
            map_image = pygame.image.load(os.path.join(images_folder, f"map{i}.png"))
            map_image = pygame.transform.scale(map_image, (400, 275))
            self.map_preview_images.append(map_image)

        self.background_img = pygame.image.load(os.path.join(images_folder, "backgrond.png"))
        self.background_img = pygame.transform.scale(self.background_img, (self.width, self.height))
        self.background_img = pygame.transform.flip(self.background_img, True, False)
        self.background_img.set_alpha(64)

    def init_ghosts(self):
        self.ghosts = []
        self.ghosts.append(Ghost(self, self.blinky_home_x[self.current_map], self.blinky_home_y[self.current_map], self.ghost_images["blinky"], self.ghost_speed, in_box=False, name="blinky"))
        self.ghosts.append(Ghost(self, self.inky_home_x[self.current_map], self.inky_home_y[self.current_map], self.ghost_images["inky"], self.ghost_speed, in_box=True, name="inky"))
        self.ghosts.append(Ghost(self, self.pinky_home_x[self.current_map], self.pinky_home_y[self.current_map], self.ghost_images["pinky"], self.ghost_speed, in_box=True, name="pinky"))
        self.ghosts.append(Ghost(self, self.clyde_home_x[self.current_map], self.clyde_home_y[self.current_map], self.ghost_images["clyde"], self.ghost_speed, in_box=True, name="clyde"))

    def draw_board(self):
        y_grid = ((self.height - 50) // 32)
        x_grid = (self.width // 30)
        for i in range(len(self.level)):
            for j in range(len(self.level[i])):
                if self.level[i][j] == 1:
                    pygame.draw.circle(self.screen, "white", (j * x_grid + 0.5 * x_grid, i * y_grid + 0.5 * y_grid), 4)
                if self.level[i][j] == 2:
                    pygame.draw.circle(self.screen, "white", (j * x_grid + 0.5 * x_grid, i * y_grid + 0.5 * y_grid), 10)
                if self.level[i][j] == 3:
                    pygame.draw.line(self.screen, "blue", (j * x_grid + 0.5 * x_grid, i * y_grid), (j * x_grid + 0.5 * x_grid, i * y_grid + y_grid), 3)
                if self.level[i][j] == 4:
                    pygame.draw.line(self.screen, "blue", (j * x_grid, i * y_grid + 0.5 * y_grid), (j * x_grid + x_grid, i * y_grid + 0.5 * y_grid), 3)
                if self.level[i][j] == 5:
                    pygame.draw.arc(self.screen, "blue", [(j * x_grid - x_grid * 0.4) - 2, (i * y_grid + 0.5 * y_grid), x_grid, y_grid], 0, self.PI / 2, 3)
                if self.level[i][j] == 6:
                    pygame.draw.arc(self.screen, "blue", [(j * x_grid + x_grid * 0.5), (i * y_grid + 0.5 * y_grid), x_grid, y_grid], self.PI / 2, self.PI, 3)
                if self.level[i][j] == 7:
                    pygame.draw.arc(self.screen, "blue", [(j * x_grid + x_grid * 0.5), (i * y_grid - 0.4 * y_grid), x_grid, y_grid], self.PI, 3 * self.PI / 2, 3)
                if self.level[i][j] == 8:
                    pygame.draw.arc(self.screen, "blue", [(j * x_grid - x_grid * 0.4) - 2, (i * y_grid - 0.4 * y_grid), x_grid, y_grid], 3 * self.PI / 2, 2 * self.PI, 3)
                if self.level[i][j] == 9:
                    pygame.draw.line(self.screen, "white", (j * x_grid, i * y_grid + 0.5 * y_grid), (j * x_grid + x_grid, i * y_grid + 0.5 * y_grid), 3)

    def with_ghost_collision(self):
        for ghost in self.ghosts:
            if abs(self.pacman.x - ghost.x) < 40 and abs(self.pacman.y - ghost.y) < 40:
                if self.chase_mode and not ghost.is_dead:
                    self.score += 200
                    self.total_pellets += 20
                    ghost.is_dead = True
                    ghost.update_path()
                elif not self.chase_mode and not ghost.is_dead:
                    self.lives -= 1
                    self.pacman.x, self.pacman.y = self.pacman_home_x[self.current_map], self.pacman_home_y[self.current_map]

                    if self.lives <= 0:
                        self.game_state = "game_over"
                    for ghost_reset in self.ghosts:
                        self.chase_mode = False
                        self.chase_counter = 0
                        self.ghost_delay_counter = 60
                        self.blinky_x = self.blinky_home_x[self.current_map]
                        self.blinky_y = self.blinky_home_y[self.current_map]
                        ghost_reset.reset_ghost()
                        ghost_reset.sober = False

    def reset_game(self):
        self.score = 0
        self.lives = self.full_health
        self.pacman.reset()
        self.chase_mode = False
        self.chase_counter = 0
        self.dots_eaten_tracker = 0
        self.total_pellets = 0
        self.level = [list(row) for row in boards[self.current_map]]
        for i, row in enumerate(self.level):
            for j, cell in enumerate(row):
                if cell == 1:
                    self.total_pellets += 1
        self.init_ghosts()
        for ghost in self.ghosts:
            ghost.reset_ghost()

    def draw_ui(self):
        score_text = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, self.height - 40))
        life_image = pygame.transform.scale(self.pacman_images[0], (60, 60))
        for i in range(self.lives):
            self.screen.blit(life_image, (self.width - 150 + i * 40, self.height - 45))

    def draw_menu(self):
        self.screen.fill("black")
        self.screen.blit(self.background_img, (0, 0))
        title_font = self._load_font("mrsmonster.ttf", 128)
        menu_title = title_font.render("Pac-Man", True, "yellow")
        title_rect = menu_title.get_rect(center=(self.width // 2, 300))
        self.screen.blit(menu_title, title_rect)

        mouse_pos = pygame.mouse.get_pos()
        menu_item_rects = []

        for i, option in enumerate(self.menu_options):
            text_color = "white"
            current_font = self._load_font("chinesefont.ttf", 48)
            menu_item = current_font.render(option, True, text_color)
            item_rect = menu_item.get_rect(center=(self.width // 2, 500 + i * 100))
            menu_item_rects.append(item_rect)

            if item_rect.collidepoint(mouse_pos):
                text_color = "green"
                current_font = self._load_font("chinesefont.ttf", 40)
                self.selected_option = i
            elif self.selected_option == i:
                text_color = "yellow"
                current_font = self._load_font("chinesefont.ttf", 52)

            menu_item = current_font.render(option, True, text_color)
            item_rect = menu_item.get_rect(center=(self.width // 2, 500 + i * 100))
            self.screen.blit(menu_item, item_rect)

        return menu_item_rects

    def draw_instructions(self):
        self.screen.fill("black")
        self.screen.blit(self.background_img, (0, 0))
        esc_font = self.chinese_font.render("(按 ESC 返回選單)", True, "white")
        exit_rect = esc_font.get_rect(topleft=(20, 20))
        self.screen.blit(esc_font, exit_rect)
        instruction_title = self.title_font.render("遊戲簡介", True, "white")
        title_rect = instruction_title.get_rect(center=(self.width // 2, 120))
        self.screen.blit(instruction_title, title_rect)

        instructions_text = [
            "你可以使用",
            "方向鍵",
            "控制 Pac-Man 移動",
            "若吃完所有白色小點便可過關",
            "過程中會有幽靈抓你",
            "你必須避開鬼魂，否則會失去一條生命",
            "失去三條命變算挑戰失敗",
            "不過吃到大的白色能量點可以在短時間追逐鬼魂",
            "並在吃掉鬼魂後獲得大量分數",
            "",
            "祝你好運!!",
        ]

        special_font = self._load_font("BoldChinese.ttf", 36)
        y_offset = 210
        for line in instructions_text:
            if line == "方向鍵":
                text = special_font.render(line, True, "yellow")
            else:
                text = self.chinese_font.render(line, True, "white")
            text_rect = text.get_rect(center=(self.width // 2, y_offset))
            self.screen.blit(text, text_rect)
            y_offset += 60

        exit_text = "返回"
        exit_font = self.title_font.render(exit_text, True, "white")
        exit_rect = exit_font.get_rect(bottomleft=(20, self.height - 20))

        mouse_pos = pygame.mouse.get_pos()
        current_exit_font = self.title_font
        exit_color = "white"

        if exit_rect.collidepoint(mouse_pos):
            exit_color = "green"
            current_exit_font = self._load_font("BoldChinese.ttf", 48)

        final_exit_text = current_exit_font.render(exit_text, True, exit_color)
        final_exit_rect = final_exit_text.get_rect(bottomleft=(20, self.height - 20))
        self.screen.blit(final_exit_text, final_exit_rect)

        return final_exit_rect

    def draw_map_select(self):
        self.screen.fill("black")
        self.background_img.set_alpha(32)
        self.screen.blit(self.background_img, (0, 0))
        self.background_img.set_alpha(64)
        esc_font = self.chinese_font.render("(按 ESC 返回選單)", True, "white")
        exit_rect = esc_font.get_rect(topleft=(20, 20))
        self.screen.blit(esc_font, exit_rect)

        map_names = ["地圖一", "地圖二", "地圖三"]
        select_rects = []
        mouse_pos = pygame.mouse.get_pos()

        for i, name in enumerate(map_names):
            y_position = 150 + 280 * i

            if i < len(self.map_preview_images):
                map_image = self.map_preview_images[i]
                map_image_rect = map_image.get_rect(center=((self.width // 2) + 20, y_position + 30))
                self.screen.blit(map_image, map_image_rect)

            select_font = self._load_font('BoldChinese.ttf', 40)
            text = select_font.render(name, True, "white")
            text_rect = text.get_rect(center=(self.width // 6, y_position - 20))
            self.screen.blit(text, text_rect)

            select_center_y = y_position + 30
            select_center = ((self.width // 6) * 5, select_center_y)
            select_color = "white"
            select_font = self._load_font('BoldChinese.ttf', 36)
            select_text = select_font.render("選擇", True, select_color)
            select_rect = select_text.get_rect(center=select_center)
            select_rects.append(select_rect)

            is_hovering = select_rect.collidepoint(mouse_pos)

            if is_hovering:
                select_color = "green"
                select_font = self._load_font('chinesefont.ttf', 32)

            if self.selected_map_index == i:
                select_color = "yellow"
                select_font = self._load_font('chinesefont.ttf', 48)

            final_select_text = select_font.render("選擇", True, select_color)
            final_select_rect = final_select_text.get_rect(center=select_center)
            self.screen.blit(final_select_text, final_select_rect)

        exit_text = "返回"
        exit_font = self.title_font.render(exit_text, True, "white")
        exit_rect = exit_font.get_rect(bottomleft=(20, self.height - 20))

        current_exit_font = self.title_font
        exit_color = "white"

        if exit_rect.collidepoint(mouse_pos):
            exit_color = "green"
            current_exit_font = pygame.font.Font("BoldChinese.ttf", 52)

        final_exit_text = current_exit_font.render(exit_text, True, exit_color)
        final_exit_rect = final_exit_text.get_rect(bottomleft=(20, self.height - 20))
        self.screen.blit(final_exit_text, final_exit_rect)

        return final_exit_rect, select_rects

    def draw_difficulty_select(self):
        self.screen.fill("black")
        self.screen.blit(self.background_img, (0, 0))
        esc_font = self.chinese_font.render("(按 ESC 返回選單)", True, "white")
        exit_rect = esc_font.get_rect(topleft=(20, 20))
        self.screen.blit(esc_font, exit_rect)

        title_text = self.title_font.render("選擇難度", True, "white")
        title_rect = title_text.get_rect(center=(self.width // 2, 80))
        self.screen.blit(title_text, title_rect)

        difficulties = ["簡單", "普通", "困難", "不可能"]
        difficulty_colors = ["green", "yellow", "orange", "red"]
        difficulty_descriptions = [
            "鬼魂速度慢，",
            "鬼魂逃跑時間長",
            "鬼魂速度適中，",
            "鬼魂逃跑一般",
            "鬼魂速度較快，",
            "鬼魂逃跑時間較短",
            "鬼魂速度極快，",
            "鬼魂逃跑時間非常短，",
            "且玩家只有一條命",
        ]
        select_rects = []

        mouse_pos = pygame.mouse.get_pos()

        y_offset = 200
        for i, difficulty in enumerate(difficulties):
            text_color = difficulty_colors[i]
            select_font = self._load_font('BoldChinese.ttf', 48)
            text = select_font.render(difficulty, True, text_color)
            text_rect = text.get_rect(midleft=(self.width // 6, y_offset + 20))
            self.screen.blit(text, text_rect)

            description_color = "white"
            description_font = self._load_font("chinesefont.ttf", 24)
            description_text = description_font.render(difficulty_descriptions[i * 2], True, description_color)
            description_rect = description_text.get_rect(midleft=(self.width * 4 // 10, y_offset))
            self.screen.blit(description_text, description_rect)
            description_text = description_font.render(difficulty_descriptions[i * 2 + 1], True, description_color)
            description_rect = description_text.get_rect(midleft=(self.width * 4 // 10, y_offset + 50))
            self.screen.blit(description_text, description_rect)
            if i == 3:
                description_text = description_font.render(difficulty_descriptions[i * 2 + 2], True, description_color)
                description_rect = description_text.get_rect(midleft=(self.width * 4 // 10, y_offset + 100))
                self.screen.blit(description_text, description_rect)

            select_color = "white"
            select_font = self._load_font('BoldChinese.ttf', 40)
            select_text = select_font.render("選擇", True, select_color)
            select_rect = select_text.get_rect(midright=(self.width * 5 // 6, y_offset + 20))
            select_rects.append(select_rect)

            is_hovering = select_rect.collidepoint(mouse_pos)
            if is_hovering:
                select_color = "green"
                select_font = self._load_font('chinesefont.ttf', 35)

            if self.selected_difficulty_index == i:
                select_color = "yellow"
                select_font = self._load_font('chinesefont.ttf', 48)

            final_select_text = select_font.render("選擇", True, select_color)
            final_select_rect = final_select_text.get_rect(midright=(self.width * 5 // 6, y_offset + 20))
            self.screen.blit(final_select_text, final_select_rect)

            y_offset += 180

        exit_text = "返回"
        exit_font = self.title_font.render(exit_text, True, "white")
        exit_rect = exit_font.get_rect(bottomleft=(20, self.height - 20))

        current_exit_font = self.title_font
        exit_color = "white"

        if exit_rect.collidepoint(mouse_pos):
            exit_color = "green"
            current_exit_font = self._load_font("BoldChinese.ttf", 52)

        final_exit_text = current_exit_font.render(exit_text, True, exit_color)
        final_exit_rect = final_exit_text.get_rect(bottomleft=(20, self.height - 20))
        self.screen.blit(final_exit_text, final_exit_rect)

        return final_exit_rect, select_rects

    def draw_game_over(self):
        self.game_over_alpha += 5
        if self.game_over_alpha > 255:
            self.game_over_alpha = 255

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self.game_over_alpha))
        self.screen.blit(overlay, (0, 0))

        title_font = self._load_font("mrsmonster.ttf", 128)
        game_over_text = title_font.render("Game Over!!", True, "red")
        game_over_rect = game_over_text.get_rect(center=(self.width // 2, self.height * 3 // 10))

        if self.game_over_alpha < 200:
            self.game_over_text_alpha -= 5
            if self.game_over_text_alpha < 0:
                self.game_over_text_alpha = 0
            inverted_overlay = pygame.Surface(game_over_text.get_size(), pygame.SRCALPHA)
            inverted_overlay.fill((255, 255, 255, 255 - self.game_over_text_alpha))
            inverted_text = game_over_text.copy()
            inverted_text.blit(inverted_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(inverted_text, game_over_rect)
        else:
            self.screen.blit(game_over_text, game_over_rect)
            self.game_over_text_alpha = 0

        restart_color = "white"
        restart_font_normal = pygame.font.Font('BoldChinese.ttf', 48)
        restart_text_surface = restart_font_normal.render("重新開始", True, restart_color)
        restart_rect = restart_text_surface.get_rect(center=(self.width // 2, self.height // 2))

        menu_color = "white"
        menu_font_normal = self._load_font('BoldChinese.ttf', 48)
        menu_text_surface = menu_font_normal.render("退回選單", True, menu_color)
        menu_rect = menu_text_surface.get_rect(center=(self.width // 2, self.height // 2 + 100))

        mouse_pos = pygame.mouse.get_pos()

        can_click_buttons = (self.game_over_alpha == 255)

        if can_click_buttons:
            if restart_rect.collidepoint(mouse_pos):
                restart_color = "green"
                restart_font_hover = pygame.font.Font('chinesefont.ttf', 36)
                restart_text_surface = restart_font_hover.render("重新開始", True, restart_color)
                restart_rect = restart_text_surface.get_rect(center=restart_rect.center)

            if menu_rect.collidepoint(mouse_pos):
                menu_color = "green"
                menu_font_hover = self._load_font('chinesefont.ttf', 36)
                menu_text_surface = menu_font_hover.render("退回選單", True, menu_color)
                menu_rect = menu_text_surface.get_rect(center=menu_rect.center)

        self.screen.blit(restart_text_surface, restart_rect)
        self.screen.blit(menu_text_surface, menu_rect)

        return restart_rect, menu_rect, can_click_buttons

    def draw_victory(self):
        self.victory_alpha += 5
        if self.victory_alpha > 255:
            self.victory_alpha = 255

        overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, self.victory_alpha))
        self.screen.blit(overlay, (0, 0))

        victory_font = self._load_font("mrsmonster.ttf", 128)
        victory_text = victory_font.render("You Win!!", True, "green")
        victory_rect = victory_text.get_rect(center=(self.width // 2, self.height * 3 // 10 - 50))
        if self.victory_alpha < 200:
            self.victory_text_alpha -= 5
            if self.victory_text_alpha < 0:
                self.victory_text_alpha = 0
            inverted_overlay = pygame.Surface(victory_text.get_size(), pygame.SRCALPHA)
            inverted_overlay.fill((255, 255, 255, 255 - self.victory_text_alpha))
            inverted_text = victory_text.copy()
            inverted_text.blit(inverted_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(inverted_text, victory_rect)
        else:
            self.screen.blit(victory_text, victory_rect)
            self.victory_text_alpha = 0

        score_font = self._load_font("chinesefont.ttf", 48)
        score_display = score_font.render(f"Final Score: {self.final_score}", True, "white")
        score_rect = score_display.get_rect(center=(self.width // 2, self.height * 3 // 10 + 50))
        self.screen.blit(score_display, score_rect)

        restart_color = "white"
        restart_font_normal = self._load_font('BoldChinese.ttf', 48)
        restart_text_surface = restart_font_normal.render("重新開始", True, restart_color)
        restart_rect = restart_text_surface.get_rect(center=(self.width // 2, self.height // 2 + 50))

        menu_color = "white"
        menu_font_normal = self._load_font('BoldChinese.ttf', 48)
        menu_text_surface = menu_font_normal.render("返回選單", True, menu_color)
        menu_rect = menu_text_surface.get_rect(center=(self.width // 2, self.height // 2 + 150))

        mouse_pos = pygame.mouse.get_pos()
        can_click_buttons = (self.victory_alpha == 255)

        if can_click_buttons:
            if restart_rect.collidepoint(mouse_pos):
                restart_color = "green"
                restart_font_hover = pygame.font.Font('chinesefont.ttf', 36)
                restart_text_surface = restart_font_hover.render("重新開始", True, restart_color)
                restart_rect = restart_text_surface.get_rect(center=restart_rect.center)

            if menu_rect.collidepoint(mouse_pos):
                menu_color = "green"
                menu_font_hover = self._load_font('chinesefont.ttf', 36)
                menu_text_surface = menu_font_hover.render("返回選單", True, menu_color)
                menu_rect = menu_text_surface.get_rect(center=menu_rect.center)

        self.screen.blit(restart_text_surface, restart_rect)
        self.screen.blit(menu_text_surface, menu_rect)

        return restart_rect, menu_rect, can_click_buttons

    def handle_playing(self, events):
        self.screen.fill("black")
        self.draw_board()
        self.pacman.draw()
        self.draw_ui()

        for ghost in self.ghosts:
            ghost.cooldown_timer += 1
            if self.pacman.collision_state:
                ghost.bfs_interval = 30
            else:
                ghost.bfs_interval = 10
                self.ghost_delay_counter -= 1
                if ghost.teleport_cooldown_timer < 30:
                    ghost.teleport_cooldown_timer += 1
                if not self.ghost_delay_counter:
                    ghost.update_path()
            if self.chase_mode:
                ghost.chase_move()
            else:
                ghost.move()
            ghost.draw()

        self.with_ghost_collision()

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    self.pacman.direction = 0
                    self.pacman.collision_state = False
                elif event.key == pygame.K_LEFT:
                    self.pacman.direction = 1
                    self.pacman.collision_state = False
                elif event.key == pygame.K_UP:
                    self.pacman.direction = 2
                    self.pacman.collision_state = False
                elif event.key == pygame.K_DOWN:
                    self.pacman.direction = 3
                    self.pacman.collision_state = False

        self.pacman.move()

        if self.chase_mode:
            self.chase_counter += 1
            if self.chase_counter >= self.chase_duration:
                self.chase_mode = False
                self.chase_counter = 0
                for ghost in self.ghosts:
                    ghost.sober = False

        if self.lives <= 0:
            self.game_state = "game_over"

        if self.score >= self.total_pellets * 10:
            self.game_state = "victory"
            self.final_score = self.score
            self.victory_alpha = 0
            self.victory_text_alpha = 255

    def run(self):
        run = True
        while run:
            self.timer.tick(self.fps)
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    run = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.game_state != "playing":
                            self.game_state = "menu"

            if self.game_state == "menu":
                menu_rects = self.draw_menu()
                for event in events:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_DOWN:
                            self.selected_option = (self.selected_option + 1) % len(self.menu_options)
                        elif event.key == pygame.K_UP:
                            self.selected_option = (self.selected_option - 1) % len(self.menu_options)
                        elif event.key == pygame.K_RETURN:
                            if self.selected_option == 0:
                                self.game_state = "map_select"
                            elif self.selected_option == 1:
                                self.game_state = "instructions"
                            elif self.selected_option == 2:
                                self.game_state = "difficulty_select"
                            elif self.selected_option == 3:
                                run = False
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if menu_rects[0].collidepoint(mouse_pos):
                            self.game_state = "map_select"
                        elif menu_rects[1].collidepoint(mouse_pos):
                            self.game_state = "instructions"
                        elif menu_rects[2].collidepoint(mouse_pos):
                            self.game_state = "difficulty_select"
                        elif menu_rects[3].collidepoint(mouse_pos):
                            run = False

            elif self.game_state == "playing":
                self.handle_playing(events)

            elif self.game_state == "instructions":
                exit_button_rect = self.draw_instructions()
                for event in events:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.game_state = "menu"
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if exit_button_rect.collidepoint(mouse_pos):
                            self.game_state = "menu"

            elif self.game_state == "difficulty_select":
                exit_button_rect, select_buttons_rects = self.draw_difficulty_select()
                for event in events:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.game_state = "menu"
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if exit_button_rect.collidepoint(mouse_pos):
                            self.game_state = "menu"
                        for i, rect in enumerate(select_buttons_rects):
                            if rect.collidepoint(mouse_pos):
                                self.selected_difficulty_index = i
                                if i == 0:
                                    self.ghost_speed = 1
                                    self.chase_duration = 10 * self.fps
                                    self.full_health = 3
                                elif i == 1:
                                    self.ghost_speed = 1.3
                                    self.chase_duration = 8 * self.fps
                                    self.full_health = 3
                                elif i == 2:
                                    self.ghost_speed = 1.5
                                    self.chase_duration = 6 * self.fps
                                    self.full_health = 3
                                elif i == 3:
                                    self.ghost_speed = 2
                                    self.chase_duration = 4 * self.fps
                                    self.full_health = 1

            elif self.game_state == "map_select":
                exit_button_rect, select_buttons_rects = self.draw_map_select()
                for event in events:
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        self.game_state = "menu"
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if exit_button_rect.collidepoint(mouse_pos):
                            self.game_state = "menu"
                        for i, rect in enumerate(select_buttons_rects):
                            if rect.collidepoint(mouse_pos):
                                self.selected_map_index = i
                                self.current_map = i
                                self.reset_game()
                                self.game_state = "playing"

            elif self.game_state == "game_over":
                self.screen.fill("black")
                restart_button, menu_button, can_click = self.draw_game_over()
                for event in events:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if can_click:
                            if restart_button.collidepoint(mouse_pos):
                                self.reset_game()
                                self.game_state = "playing"
                                self.game_over_alpha = 0
                                self.game_over_text_alpha = 255
                            elif menu_button.collidepoint(mouse_pos):
                                self.game_state = "menu"
                                self.game_over_alpha = 0
                                self.game_over_text_alpha = 255

            elif self.game_state == "victory":
                self.screen.fill("black")
                restart_button, menu_button, can_click = self.draw_victory()
                for event in events:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_pos = event.pos
                        if can_click:
                            if restart_button.collidepoint(mouse_pos):
                                self.reset_game()
                                self.game_state = "playing"
                                self.victory_alpha = 0
                                self.victory_text_alpha = 255
                            elif menu_button.collidepoint(mouse_pos):
                                self.game_state = "menu"
                                self.victory_alpha = 0
                                self.victory_text_alpha = 255

            pygame.display.flip()

        pygame.quit()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()

def bfs(grid, start, end):
    rows, cols = len(grid), len(grid[0])
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    queue = deque([(start[0], start[1], [])])
    visited = set()
    visited.add((start[0], start[1]))

    while queue:
        x, y, path = queue.popleft()
        if (x, y) == end:
            return path
        for dx, dy in directions:
            nx, ny = x + dx, y + dy
            if ny < 0:
                ny = cols - 1
            elif ny >= cols:
                ny = 0

            if 0 <= nx < rows and (nx, ny) not in visited:
                if grid[nx][ny] < 3 or grid[nx][ny] == 9:
                    queue.append((nx, ny, path + [(nx, ny)]))
                    visited.add((nx, ny))
    print("no path is founded")
    return []

def draw_path(path, screen, x_grid, y_grid):
    if path:
        for row, col in path:
            x = col * x_grid + x_grid // 2  
            y = row * y_grid + y_grid // 2  
            pygame.draw.circle(screen, (255, 0, 0), (x, y), 4)

class Ghost:
    def __init__(self, x, y, image, speed, in_box=True, name="ghost"):
        self.x = x
        self.y = y
        self.image = image
        self.normal_image = image
        self.speed = speed
        self.direction = 0
        self.in_box = in_box
        self.name = name
        self.path = []
        self.path_index = 0
        self.bfs_interval = 10
        self.bfs_counter = 0
        self.chase_image = ghost_images["chase"]
        self.dead_image = ghost_images["dead"]
        self.is_dead = False
        self.sober = False
        self.cooldown_timer = 20
        self.teleport_cooldown_timer = 30
        self.revive_timer = 0

    def update_path(self):
        global level, pacman_X, pacman_Y, direction, blinky_X, blinky_Y, score
        y_grid = ((HEIGHT - 50) // 32)  
        x_grid = (WIDTH // 30)  
        row = int((self.y + 30) // y_grid)  
        col = int((self.x + 30) // x_grid)  
        pacman_row = int((pacman_Y + 40) // y_grid)  
        pacman_col = int((pacman_X + 40) // x_grid)  

        if self.name == "blinky":
            if self.is_dead:
                self.path = bfs(level, (row, col), ((pinky_homeY[current_map] + 30) // y_grid, (pinky_homeX[current_map] + 30) // x_grid)) 
            else:
                self.path = bfs(level, (row, col), (pacman_row, pacman_col))
                blinky_X = self.x
                blinky_Y = self.y

        elif self.name == "pinky":
            if self.is_dead:
                self.path = bfs(level, (row, col), ((pinky_homeY[current_map] + 30) // y_grid, (pinky_homeX[current_map] + 30) // x_grid)) 
            else:
                target_pacman_row = int((pacman_Y + 40) // y_grid) 
                target_pacman_col = int((pacman_X + 40) // x_grid) 

                if(self.cooldown_timer < chase_switch_timer):
                    pass
                elif(math.pow(col - target_pacman_col,2) + math.pow(row - target_pacman_row,2)) <= 16:
                    self.cooldowntimer = 0
                    self.path = bfs(level, (row, col), (target_pacman_row, target_pacman_col))
                else:
                    self.cooldowntimer = 0
                    prediction_steps = 4
                    predicted_row = target_pacman_row
                    predicted_col = target_pacman_col

                    if direction == 0:  # Right
                        predicted_col += prediction_steps
                    elif direction == 1:  # Left
                        predicted_col -= prediction_steps
                    elif direction == 2:  # Up
                        predicted_row -= prediction_steps
                    elif direction == 3:  # Down
                        predicted_row += prediction_steps

                    if 0 <= predicted_row < len(level) and 0 <= predicted_col < len(level[0]) and level[predicted_row][predicted_col] < 3:
                        self.path = bfs(level, (row, col), (predicted_row, predicted_col))
                    else:
                        found_valid_target = False
                        for steps in range(prediction_steps, -1, -1):
                            check_row, check_col = target_pacman_row, target_pacman_col
                            if direction == 0:
                                check_col += steps
                            elif direction == 1:
                                check_col -= steps
                            elif direction == 2:
                                check_row -= steps
                            elif direction == 3:
                                check_row += steps

                            if (0 <= check_row < len(level) and 0 <= check_col < len(level[0]) and level[check_row][check_col] < 3):
                                self.path = bfs(level, (row, col), (check_row, check_col))
                                found_valid_target = True
                                break  

                        if not found_valid_target:
                            self.path = bfs(level, (row, col), (target_pacman_row, target_pacman_col))

        elif self.name == "clyde":
            if self.is_dead:
                self.path = bfs(level, (row, col), ((clyde_homeY[current_map] + 30) // y_grid, (clyde_homeX[current_map] + 30)  // x_grid))
            else:
                if score >= 600:
                    if(self.cooldown_timer < chase_switch_timer):
                        pass
                    elif(math.pow(col - pacman_col,2) + math.pow(row - pacman_row,2)) <= 64:
                        self.path = bfs(level, (row, col), (850 // x_grid, 80 // y_grid)) 
                    else:
                        self.path = bfs(level, (row, col), (pacman_row, pacman_col))

        elif self.name == "inky":
            if self.is_dead:
                self.path = bfs(level, (row, col), ((inky_homeY[current_map] + 30) // y_grid, (inky_homeX[current_map] + 30)  // x_grid)) 
            else:
                if dots_eaten_tracker >= 30:
                    blinky_row = int((blinky_Y + 30) // y_grid) 
                    blinky_col = int((blinky_X + 30) // x_grid) 
                    pacman_ahead_row, pacman_ahead_col = pacman_row, pacman_col

                    if direction == 0:  # Right
                        pacman_ahead_col += 2
                    elif direction == 1:  # Left
                        pacman_ahead_col -= 2
                    elif direction == 2:  # Up
                        pacman_ahead_row -= 2
                    elif direction == 3:  # Down
                        pacman_ahead_row += 2

                    target_row = pacman_ahead_row + (pacman_ahead_row - blinky_row)
                    target_col = pacman_ahead_col + (pacman_ahead_col - blinky_col)

                    found_path = False

                    if 0 <= target_row < len(level) and 0 <= target_col < len(level[0]):
                        # 目標在界內
                        if level[target_row][target_col] < 3:
                            self.path = bfs(level, (row, col), (target_row, target_col))
                            found_path = True
                        else:
                            # 目標是牆壁
                            search_radius = 1
                            while not found_path and search_radius < max(len(level), len(level[0])):
                                for i in range(-search_radius, search_radius + 1):
                                    for j in range(-search_radius, search_radius + 1):
                                        check_row, check_col = target_row + i, target_col + j
                                        if (i == -search_radius or i == search_radius or j == -search_radius or j == search_radius) and \
                                           0 <= check_row < len(level) and 0 <= check_col < len(level[0]) and level[check_row][check_col] < 3:
                                            self.path = bfs(level, (row, col), (check_row, check_col))
                                            found_path = True
                                            break
                                    if found_path:
                                        break
                                search_radius += 1
                    else:
                        if target_row < 0:
                            for r in range(0, row + 1):
                                if 0 <= r < len(level) and 0 <= target_col < len(level[0]) and level[r][target_col] < 3:
                                    self.path = bfs(level, (row, col), (r, target_col))
                                    found_path = True
                                    break
                        elif target_row >= len(level):
                            for r in range(len(level) - 1, row - 1, -1):
                                if 0 <= r < len(level) and 0 <= target_col < len(level[0]) and level[r][target_col] < 3:
                                    self.path = bfs(level, (row, col), (r, target_col))
                                    found_path = True
                                    break
                        # check horizon
                        if not found_path:
                            if target_col < 0:
                                for c in range(0, col + 1):
                                    if 0 <= target_row < len(level) and 0 <= c < len(level[0]) and level[target_row][c] < 3:
                                        self.path = bfs(level, (row, col), (target_row, c))
                                        found_path = True
                                        break
                            elif target_col >= len(level[0]):
                                for c in range(len(level[0]) - 1, col - 1, -1):
                                    if 0 <= target_row < len(level) and 0 <= c < len(level[0]) and level[target_row][c] < 3:
                                        self.path = bfs(level, (row, col), (target_row, c))
                                        found_path = True
                                        break

                    if not found_path:
                        self.path = bfs(level, (row, col), (pacman_row, pacman_col))

        self.path_index = 0

    def move(self):
        global level
        y_grid = ((HEIGHT - 50) // 32) 
        x_grid = (WIDTH // 30)  

        self.bfs_counter += 1
        if self.bfs_counter >= self.bfs_interval:
            self.update_path()
            self.bfs_counter = 0

        if self.path:
            if self.path_index < len(self.path):
                self.in_box = False
                target_row, target_col = self.path[self.path_index]
                target_x = target_col * x_grid + x_grid // 2 - 30 
                target_y = target_row * y_grid + y_grid // 2 - 30 

                dx = target_x - self.x
                dy = target_y - self.y

                move_x = min(abs(dx), self.speed) * (1 if dx > 0 else -1 if dx < 0 else 0)
                move_y = min(abs(dy), self.speed) * (1 if dy > 0 else -1 if dy < 0 else 0)

                self.x += move_x
                self.y += move_y

                row = int((self.y + 30) // y_grid)  
                col = int((self.x + 30) // x_grid) 

                #pygame.draw.circle(screen, (0, 255, 0), (self.x + 30, self.y), 4)
                #pygame.draw.circle(screen, (0, 255, 0), (WIDTH - y_grid, self.y), 4)

                if level[row][col] == -1 and self.teleport_cooldown_timer >= 30:
                    if self.x + 30 <= x_grid // 2 + 10: 
                        #print("teleport1", self.teleport_cooldown_timer)
                        self.x = WIDTH - x_grid - 30 
                        self.teleport_cooldown_timer = 0
                    elif self.x + 30 >= WIDTH - x_grid: 
                        #print("teleport2", self.teleport_cooldown_timer)
                        self.x = x_grid // 2 - 30 
                        self.teleport_cooldown_timer = 0

                if abs(self.x - target_x) < 2 and abs(self.y - target_y) < 2:
                    self.path_index += 1
            else:
                self.path = []
                self.path_index = 0
        if self.is_dead:
            #print(move_x**2+move_y**2) 
            if self.name == "blinky":
                houseX = pinky_homeX[current_map]
                houseY = pinky_homeY[current_map]
            elif self.name == "pinky":
                houseX = pinky_homeX[current_map]
                houseY = pinky_homeY[current_map]
            elif self.name == "clyde":
                houseX = clyde_homeX[current_map]
                houseY = clyde_homeY[current_map]
            elif self.name == "inky":
                houseX = inky_homeX[current_map]
                houseY = inky_homeY[current_map]
            if abs(self.x - houseX) < 30 and abs(self.y - houseY) < 30:
                self.revive_timer += 1
                self.in_box = True
                if(self.revive_timer >= 30):
                    print(self.name, "return") 
                    self.is_dead = False
                    self.image = self.normal_image
                    self.sober = True
                    self.revive_timer = 0

    def chase_move(self):
        global level, pacman_X, pacman_Y
        y_grid = ((HEIGHT - 50) // 32)
        x_grid = (WIDTH // 30)
        row = int((self.y + 30) // y_grid)
        col = int((self.x + 30) // x_grid)

        if chase_mode and not self.is_dead and not self.sober and not self.in_box:
            dx = pacman_X - self.x
            dy = pacman_Y - self.y

            # check forward
            can_move_forward = True
            if self.direction == 0 and level[row][col - 1] >= 3:
                can_move_forward = False
            elif self.direction == 1 and level[row][col + 1] >= 3:
                can_move_forward = False
            elif self.direction == 2 and level[row - 1][col] >= 3:
                can_move_forward = False
            elif self.direction == 3 and level[row + 1][col] >= 3:
                can_move_forward = False

            if can_move_forward:
                if self.direction == 0:
                    self.x -= self.speed-0.5
                elif self.direction == 1:
                    self.x += self.speed-0.5
                elif self.direction == 2:
                    self.y -= self.speed-0.5
                elif self.direction == 3:
                    self.y += self.speed-0.5
            else:
                possible_moves = []
                # check left
                if level[row][col - 1] < 3 and self.direction != 1:
                    possible_moves.append(0)
                # check right
                if level[row][col + 1] < 3 and self.direction != 0:
                    possible_moves.append(1)
                # check up
                if level[row - 1][col] < 3 and self.direction != 3:
                    possible_moves.append(2)
                # check down
                if level[row + 1][col] < 3 and self.direction != 2:
                    possible_moves.append(3)

                if possible_moves:
                    # find best path
                    best_direction = -1
                    max_distance_sq = float("-inf") 

                    for direction in possible_moves:
                        next_x, next_y = self.x, self.y
                        if direction == 0:
                            next_x -= x_grid 
                        elif direction == 1:
                            next_x += x_grid 
                        elif direction == 2:
                            next_y -= y_grid 
                        elif direction == 3:
                            next_y += y_grid 

                        distance_sq = pow(pacman_X - next_x, 2) + pow(pacman_Y - next_y, 2)
                        if distance_sq > max_distance_sq: 
                            max_distance_sq = distance_sq
                            best_direction = direction

                    if best_direction != -1:
                        self.direction = best_direction
                        if self.direction == 0:
                            self.x -= self.speed
                        elif self.direction == 1:
                            self.x += self.speed
                        elif self.direction == 2:
                            self.y -= self.speed
                        elif self.direction == 3:
                            self.y += self.speed
                else:
                    # direction stays
                    if self.direction == 0 and level[row][col - 1] < 3:
                        self.x -= self.speed
                    elif self.direction == 1 and level[row][col + 1] < 3:
                        self.x += self.speed
                    elif self.direction == 2 and level[row - 1][col] < 3:
                        self.y -= self.speed
                    elif self.direction == 3 and level[row + 1][col] < 3:
                        self.y += self.speed

    def draw(self):
        if chase_mode and not self.is_dead and not self.sober and not self.in_box:
            screen.blit(self.chase_image, (self.x, self.y))
        elif self.is_dead:
            #print("he dead")
            screen.blit(self.dead_image, (self.x, self.y))
            self.move()  
        else:
            screen.blit(self.image, (self.x, self.y))

    def reset_ghost(self):
        self.sober = False
        if self.name == "blinky":
            self.x = blinky_homeX[current_map]
            self.y = blinky_homeY[current_map]
        elif self.name == "inky":
            self.x = inky_homeX[current_map]
            self.y = inky_homeY[current_map]
            self.in_box = True
        elif self.name == "pinky":
            self.x = pinky_homeX[current_map]
            self.y = pinky_homeY[current_map]
            self.in_box = True
        elif self.name == "clyde":
            self.x = clyde_homeX[current_map]
            self.y = clyde_homeY[current_map]
            self.in_box = True

        if self.is_dead:
            self.is_dead = False
            self.image = self.normal_image
            

def load_images():
    global collision_image, ghost_images, pacman_images, map_preview_images, background_img
    script_dir = os.path.dirname(os.path.abspath(__file__))
    images_folder = os.path.join(script_dir, "images")

    pacman_images = [
        pygame.transform.scale(pygame.image.load(os.path.join(images_folder, f"pacman{i}.png")), (80, 80))
        for i in range(1, 5)
    ]
    collision_image = pygame.transform.scale(
        pygame.image.load(os.path.join(images_folder, "collision.png")), (80, 80)
    )

    ghost_images = {
        "blinky": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "red.png")), (60, 60)),
        "inky": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "inky.png")), (60, 60)),
        "pinky": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "pinky.png")), (60, 60)),
        "clyde": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "clyde.png")), (60, 60)),
        "chase": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "chase.png")), (60, 60)),
        "dead": pygame.transform.scale(pygame.image.load(os.path.join(images_folder, "dead.png")), (80, 80)),
    }

    map_preview_images = []
    for i in range(1, 4):
        map_image = pygame.image.load(os.path.join(images_folder, f'map{i}.png'))
        map_image = pygame.transform.scale(map_image, (400, 275))
        map_preview_images.append(map_image)

    background_img = pygame.image.load(os.path.join(images_folder, "backgrond.png"))
    background_img = pygame.transform.scale(background_img, (WIDTH, HEIGHT))
    background_img = pygame.transform.flip(background_img, True, False)
    background_img.set_alpha(64)

def init_ghosts():
    ghosts.append(Ghost(blinky_homeX[current_map], blinky_homeY[current_map], ghost_images["blinky"], ghost_speed, in_box=False, name="blinky"))
    ghosts.append(Ghost(inky_homeX[current_map], inky_homeY[current_map], ghost_images["inky"], ghost_speed, in_box=True, name="inky"))
    ghosts.append(Ghost(pinky_homeX[current_map], pinky_homeY[current_map], ghost_images["pinky"], ghost_speed, in_box=True, name="pinky"))
    ghosts.append(Ghost(clyde_homeX[current_map], clyde_homeY[current_map], ghost_images["clyde"], ghost_speed, in_box=True, name="clyde"))

def draw_board():
    y_grid = ((HEIGHT - 50) // 32)
    x_grid = (WIDTH // 30)
    for i in range(len(level)):
        for j in range(len(level[i])):
            if level[i][j] == 1:
                pygame.draw.circle(screen, "white", (j*x_grid + 0.5*x_grid, i*y_grid + 0.5*y_grid), 4)
            if level[i][j] == 2:
                pygame.draw.circle(screen, "white", (j*x_grid + 0.5*x_grid, i*y_grid + 0.5*y_grid), 10)
            if level[i][j] == 3:
                pygame.draw.line(screen, "blue", (j*x_grid + 0.5*x_grid, i*y_grid), (j*x_grid + 0.5*x_grid, i*y_grid + y_grid), 3)
            if level[i][j] == 4:
                pygame.draw.line(screen, "blue", (j*x_grid, i*y_grid + 0.5*y_grid), (j*x_grid + x_grid, i*y_grid + 0.5*y_grid), 3)
            if level[i][j] == 5:
                pygame.draw.arc(screen, "blue", [(j*x_grid - x_grid*0.4) - 2, (i*y_grid + 0.5*y_grid), x_grid, y_grid], 0, PI/2, 3)
            if level[i][j] == 6:
                pygame.draw.arc(screen, "blue", [(j*x_grid + x_grid*0.5), (i*y_grid + 0.5*y_grid), x_grid, y_grid], PI/2, PI, 3)
            if level[i][j] == 7:
                pygame.draw.arc(screen, "blue", [(j*x_grid + x_grid*0.5), (i*y_grid - 0.4*y_grid), x_grid, y_grid], PI, 3*PI/2, 3)
            if level[i][j] == 8:
                pygame.draw.arc(screen, "blue", [(j*x_grid - x_grid*0.4) - 2, (i*y_grid - 0.4*y_grid), x_grid, y_grid], 3*PI/2, 2*PI, 3)
            if level[i][j] == 9:
                pygame.draw.line(screen, "white", (j*x_grid, i*y_grid + 0.5*y_grid), (j*x_grid + x_grid, i*y_grid + 0.5*y_grid), 3)

def draw_pacman():
    global counter, collision_state
    if collision_state:
        image = collision_image 
    else:
        image = pacman_images[counter // 5 % len(pacman_images)]
    if direction == 0: 
        screen.blit(image, (pacman_X, pacman_Y))
    elif direction == 1:  
        screen.blit(pygame.transform.flip(image, True, False), (pacman_X, pacman_Y))
    elif direction == 2:  
        screen.blit(pygame.transform.rotate(image, 90), (pacman_X, pacman_Y))
    elif direction == 3:  
        screen.blit(pygame.transform.rotate(image, -90), (pacman_X, pacman_Y))
    counter += 1

def check_collision(new_x, new_y):
    y_grid = ((HEIGHT - 50) // 32)
    x_grid = (WIDTH // 30)
    row = int((new_y + 40) // y_grid)  
    col = int((new_x + 40) // x_grid)  
    if col <= 0 or col >= 30:
        return False
    elif level[row][col] >= 3:
        return True
    return False

def move_pacman():
    global pacman_X, pacman_Y, collision_state, score, lives, direction, chase_mode, chase_counter, dots_eaten_tracker, total_pellets
    y_grid = ((HEIGHT - 50) // 32)
    x_grid = (WIDTH // 30)
    new_x, new_y = pacman_X, pacman_Y

    if not collision_state:
        if direction == 0:
            new_x += player_speed
        elif direction == 1:
            new_x -= player_speed
        elif direction == 2:
            new_y -= player_speed
        elif direction == 3:
            new_y += player_speed

        if check_collision(new_x, new_y):
            collision_state = True
        else:
            pacman_X, pacman_Y = new_x, new_y
            row = int((pacman_Y + 40) // y_grid)  
            col = int((pacman_X + 40) // x_grid)  
            #pygame.draw.circle(screen, (0, 255, 255), (pacman_X + 40, pacman_Y + 40), 4)
            if pacman_X + 40 <= 0:
                pacman_X = 890 - 40
                col = int((pacman_X + 40) // x_grid)  
                for ghost in ghosts:
                    ghost.bfs_counter = ghost.bfs_interval
                    ghost.move()
            elif pacman_X + 40 >= 900:
                pacman_X = 10 - 40
                col = int((pacman_X + 40) // x_grid)  
                for ghost in ghosts:
                    ghost.bfs_counter = ghost.bfs_interval
                    ghost.move()

            if 0 <= row < len(level) and 0 <= col < len(level[0]):
                if level[row][col] == 1:
                    score += 10
                    level[row][col] = 0
                    dots_eaten_tracker += 1
                elif level[row][col] == 2:
                    score += 50
                    total_pellets += 5
                    level[row][col] = 0
                    for ghost in ghosts:
                        ghost.sober = False
                    chase_mode = True
                    chase_counter = 0

def with_ghost_collision():
    global lives, pacman_X, pacman_Y, score, chase_mode, total_pellets
    y_grid = ((HEIGHT - 50) // 32)
    x_grid = (WIDTH // 30)
    for ghost in ghosts:
        if abs(pacman_X - ghost.x) < 40 and abs(pacman_Y - ghost.y) < 40:
            if chase_mode and not ghost.is_dead:
                score += 200
                total_pellets += 20
                ghost.is_dead = True
                """row = int((ghost.y + 30) // y_grid) 
                col = int((ghost.x + 30) // x_grid) 
                if level[row][col] >= 3:
                    print("blinky is our of path:",level[row][col])
                    
                ghost.x = col * x_grid - 30
                ghost.y = row * y_grid - 30

                row = int((blinky_homeY[current_map]+30) // y_grid) 
                col = int(450 // x_grid) 
                if level[row][col] >= 3:
                    print("blinky_home is our of path:",level[row][col])"""

                ghost.update_path()
            elif not chase_mode and not ghost.is_dead:
                lives -= 1
                pacman_X, pacman_Y = pacman_homeX[current_map], pacman_homeY[current_map]

                if lives <= 0:
                    global game_state
                    game_state = "game_over"
                for ghost in ghosts:
                    chase_mode = False
                    global chase_counter
                    chase_counter = 0
                    global ghost_delay_counter
                    ghost_delay_counter = 60
                    global blinky_X, blinky_Y
                    blinky_X = blinky_homeX[current_map]
                    blinky_Y = blinky_homeY[current_map]
                    ghost.reset_ghost()
                    ghost.sober = False

def reset_game():
    global score, lives, pacman_X, pacman_Y, direction, collision_state, ghosts, chase_mode, chase_counter, dots_eaten_tracker, level, total_pellets, current_map
    score = 0
    lives = full_health
    direction = 0
    pacman_X = pacman_homeX[current_map]
    pacman_Y = pacman_homeY[current_map]
    collision_state = False
    ghosts = []
    chase_mode = False
    chase_counter = 0
    dots_eaten_tracker = 0
    total_pellets = 0
    """ 
    if(level == boards[current_map]):
    print("useless")
    """
    level = [list(row) for row in boards[current_map]]
    for i, row in enumerate(level):
        for j, cell in enumerate(row):
            if cell == 1:
                total_pellets += 1
    draw_board()
    init_ghosts()
    for ghost in ghosts:
        ghost.reset_ghost()

def draw_ui():
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(score_text, (10, HEIGHT - 40))
    for i in range(3):
        life_image = pygame.transform.scale(pacman_images[i], (60, 60))
    for i in range(lives):
        screen.blit(life_image, (WIDTH - 150 + i * 40, HEIGHT - 45))

def draw_menu():
    screen.fill("black")
    screen.blit(background_img, (0, 0))
    title_font = pygame.font.Font("mrsmonster.ttf", 128)
    menu_title = title_font.render("Pac-Man", True, "yellow")
    title_rect = menu_title.get_rect(center=(WIDTH // 2, 300))
    screen.blit(menu_title, title_rect)

    mouse_pos = pygame.mouse.get_pos()
    global selected_option

    menu_item_rects = [] 

    for i, option in enumerate(menu_options):
        text_color = "white"
        current_font = pygame.font.Font("chinesefont.ttf", 48)
        menu_item = current_font.render(option, True, text_color)
        item_rect = menu_item.get_rect(center=(WIDTH // 2, 500 + i * 100))
        menu_item_rects.append(item_rect) 

        # mouse
        if item_rect.collidepoint(mouse_pos):
            text_color = "green"
            current_font = pygame.font.Font("chinesefont.ttf", 40)
            selected_option = i 
        #keyboard
        elif selected_option == i:
            text_color = "yellow" 
            current_font = pygame.font.Font("chinesefont.ttf", 52) 

        menu_item = current_font.render(option, True, text_color)
        item_rect = menu_item.get_rect(center=(WIDTH // 2, 500 + i * 100))
        screen.blit(menu_item, item_rect)

    return menu_item_rects
   

def draw_instructions():
    screen.fill("black")
    screen.blit(background_img, (0, 0))
    ESC_font = chinese_font.render("(按 ESC 返回選單)", True, "white")
    exit_rect = ESC_font.get_rect(topleft=(20, 20)) 
    screen.blit(ESC_font, exit_rect)
    instruction_title = title_font.render("遊戲簡介", True, "white")
    title_rect = instruction_title.get_rect(center=(WIDTH // 2, 120))
    screen.blit(instruction_title, title_rect)

    instructions_text = [
        "你可以使用",
        "方向鍵",
        "控制 Pac-Man 移動",
        "若吃完所有白色小點便可過關",
        "過程中會有幽靈抓你",
        "你必須避開鬼魂，否則會失去一條生命",
        "失去三條命變算挑戰失敗",
        "不過吃到大的白色能量點可以在短時間追逐鬼魂",
        "並在吃掉鬼魂後獲得大量分數",
        "",
        "祝你好運!!",
    ]

    special_font = pygame.font.Font("BoldChinese.ttf", 36) 
    y_offset = 210
    for line in instructions_text:
        if line == "方向鍵":
            text = special_font.render(line, True, "yellow")
        else:
            text = chinese_font.render(line, True, "white")
        text_rect = text.get_rect(center=(WIDTH // 2, y_offset))
        screen.blit(text, text_rect)
        y_offset += 60

    exit_text = "返回"
    exit_font = title_font.render(exit_text, True, "white")
    exit_rect = exit_font.get_rect(bottomleft=(20, HEIGHT - 20))

    mouse_pos = pygame.mouse.get_pos()
    current_exit_font = title_font
    exit_color = "white"

    if exit_rect.collidepoint(mouse_pos):
        exit_color = "green"
        current_exit_font = pygame.font.Font("BoldChinese.ttf", 48)

    final_exit_text = current_exit_font.render(exit_text, True, exit_color)
    final_exit_rect = final_exit_text.get_rect(bottomleft=(20, HEIGHT - 20))
    screen.blit(final_exit_text, final_exit_rect)

    return final_exit_rect
    
def draw_map_select():
    screen.fill("black")
    background_img.set_alpha(32)
    screen.blit(background_img, (0, 0))
    background_img.set_alpha(64)
    ESC_font = chinese_font.render("(按 ESC 返回選單)", True, "white")
    exit_rect = ESC_font.get_rect(topleft=(20, 20))
    screen.blit(ESC_font, exit_rect)

    map_names = ["地圖一", "地圖二", "地圖三"]
    select_rects = []
    global selected_map_index 

    mouse_pos = pygame.mouse.get_pos() 

    for i, name in enumerate(map_names):
        y_position = 150 + 280 * i

        if i < len(map_preview_images):
            map_image = map_preview_images[i]
            map_image_rect = map_image.get_rect(center=((WIDTH // 2) + 20, y_position + 30))
            screen.blit(map_image, map_image_rect)

        select_font = pygame.font.Font('BoldChinese.ttf', 40)
        text = select_font.render(name, True, "white")
        text_rect = text.get_rect(center=(WIDTH // 6, y_position - 20))
        screen.blit(text, text_rect)

        select_center_y = y_position + 30
        select_center = ((WIDTH // 6) * 5, select_center_y)
        select_color = "white"
        select_font = pygame.font.Font('BoldChinese.ttf', 36)
        select_text = select_font.render("選擇", True, select_color)
        select_rect = select_text.get_rect(center=select_center)
        select_rects.append(select_rect)

        is_hovering = select_rect.collidepoint(mouse_pos)

        if is_hovering:
            select_color = "green"
            select_font = pygame.font.Font('chinesefont.ttf', 32)

        if selected_map_index == i:
            select_color = "yellow"
            select_font = pygame.font.Font('chinesefont.ttf', 48)

        final_select_text = select_font.render("選擇", True, select_color)
        final_select_rect = final_select_text.get_rect(center=select_center)
        screen.blit(final_select_text, final_select_rect)

    exit_text = "返回"
    exit_font = title_font.render(exit_text, True, "white")
    exit_rect = exit_font.get_rect(bottomleft=(20, HEIGHT - 20))

    current_exit_font = title_font
    exit_color = "white"

    if exit_rect.collidepoint(mouse_pos):
        exit_color = "green"
        current_exit_font = pygame.font.Font("BoldChinese.ttf", 52)

    final_exit_text = current_exit_font.render(exit_text, True, exit_color)
    final_exit_rect = final_exit_text.get_rect(bottomleft=(20, HEIGHT - 20))
    screen.blit(final_exit_text, final_exit_rect)

    return final_exit_rect, select_rects

def draw_difficulty_select():
    screen.fill("black")
    screen.blit(background_img, (0, 0))
    ESC_font = chinese_font.render("(按 ESC 返回選單)", True, "white")
    exit_rect = ESC_font.get_rect(topleft=(20, 20)) 
    screen.blit(ESC_font, exit_rect)

    title_text = title_font.render("選擇難度", True, "white")
    title_rect = title_text.get_rect(center=(WIDTH // 2, 80)) 
    screen.blit(title_text, title_rect)

    difficulties = ["簡單", "普通", "困難", "不可能"]
    difficulty_colors = ["green", "yellow", "orange", "red"]
    difficulty_descriptions = [
        "鬼魂速度慢，",
        "鬼魂逃跑時間長",
        "鬼魂速度適中，",
        "鬼魂逃跑一般",
        "鬼魂速度較快，",
        "鬼魂逃跑時間較短",
        "鬼魂速度極快，",
        "鬼魂逃跑時間非常短，",
        "且玩家只有一條命"
    ]
    select_rects = []
    global selected_difficulty_index

    mouse_pos = pygame.mouse.get_pos()

    y_offset = 200
    for i, difficulty in enumerate(difficulties):
        # difficulty
        text_color = difficulty_colors[i]
        font = chinese_font
        select_font = pygame.font.Font('BoldChinese.ttf', 48) 
        text = select_font.render(difficulty, True, text_color)
        text_rect = text.get_rect(midleft=(WIDTH // 6, y_offset+20))
        screen.blit(text, text_rect)
        # introduction
        description_color = "white"
        description_font = pygame.font.Font("chinesefont.ttf", 24)
        description_text = description_font.render(difficulty_descriptions[i*2], True, description_color)
        description_rect = description_text.get_rect(midleft=(WIDTH*4 // 10, y_offset))
        screen.blit(description_text, description_rect)
        description_text = description_font.render(difficulty_descriptions[i*2+1], True, description_color)
        description_rect = description_text.get_rect(midleft=(WIDTH*4 // 10, y_offset+50))
        screen.blit(description_text, description_rect)
        if i == 3:
            description_text = description_font.render(difficulty_descriptions[i*2+2], True, description_color)
            description_rect = description_text.get_rect(midleft=(WIDTH*4 // 10, y_offset+100))
            screen.blit(description_text, description_rect)
        # select
        select_color = "white"
        select_font = pygame.font.Font('BoldChinese.ttf',40) 
        select_text = select_font.render("選擇", True, select_color)
        select_rect = select_text.get_rect(midright=(WIDTH * 5 // 6, y_offset+20))
        select_rects.append(select_rect)

        is_hovering = select_rect.collidepoint(mouse_pos)
        if is_hovering:
            select_color = "green"
            select_font = pygame.font.Font('chinesefont.ttf', 35)

        if selected_difficulty_index == i:
            select_color = "yellow"
            select_font = pygame.font.Font('chinesefont.ttf', 48) 

        final_select_text = select_font.render("選擇", True, select_color)
        final_select_rect = final_select_text.get_rect(midright=(WIDTH * 5 // 6, y_offset+20))
        screen.blit(final_select_text, final_select_rect)

        y_offset += 180

    exit_text = "返回"
    exit_font = title_font.render(exit_text, True, "white")
    exit_rect = exit_font.get_rect(bottomleft=(20, HEIGHT - 20)) 

    current_exit_font = title_font
    exit_color = "white"

    if exit_rect.collidepoint(mouse_pos):
        exit_color = "green"
        current_exit_font = pygame.font.Font("BoldChinese.ttf", 52)

    final_exit_text = current_exit_font.render(exit_text, True, exit_color)
    final_exit_rect = final_exit_text.get_rect(bottomleft=(20, HEIGHT - 20))
    screen.blit(final_exit_text, final_exit_rect)

    return final_exit_rect, select_rects

def draw_game_over():
    global game_over_alpha, game_over_text_alpha
    game_over_alpha += 5
    if game_over_alpha > 255:
        game_over_alpha = 255

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, game_over_alpha))
    screen.blit(overlay, (0, 0))

    title_font = pygame.font.Font("mrsmonster.ttf", 128)
    game_over_text = title_font.render("Game Over!!", True, "red")
    game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT * 3 // 10))

    if game_over_alpha < 200: # 全黑前
        game_over_text_alpha -= 5
        if game_over_text_alpha < 0:
            game_over_text_alpha = 0
        inverted_overlay = pygame.Surface(game_over_text.get_size(), pygame.SRCALPHA)
        inverted_overlay.fill((255, 255, 255, 255 - game_over_text_alpha)) 
        inverted_text = game_over_text.copy()
        inverted_text.blit(inverted_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(inverted_text, game_over_rect)
    else:
        screen.blit(game_over_text, game_over_rect)
        game_over_text_alpha = 0 # 不再變透明

    
    restart_color = "white"
    restart_font_normal = pygame.font.Font('BoldChinese.ttf', 48)
    restart_text_surface = restart_font_normal.render("重新開始", True, restart_color)
    restart_rect = restart_text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2))

    menu_color = "white"
    menu_font_normal = pygame.font.Font('BoldChinese.ttf', 48)
    menu_text_surface = menu_font_normal.render("退回選單", True, menu_color)
    menu_rect = menu_text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 100))

    mouse_pos = pygame.mouse.get_pos()

    can_click_buttons = (game_over_alpha == 255) 

    if can_click_buttons:
        if restart_rect.collidepoint(mouse_pos):
            restart_color = "green"
            restart_font_hover = pygame.font.Font('chinesefont.ttf', 36)
            restart_text_surface = restart_font_hover.render("重新開始", True, restart_color)
            restart_rect = restart_text_surface.get_rect(center=restart_rect.center)

        if menu_rect.collidepoint(mouse_pos):
            menu_color = "green"
            menu_font_hover = pygame.font.Font('chinesefont.ttf', 36)
            menu_text_surface = menu_font_hover.render("退回選單", True, menu_color)
            menu_rect = menu_text_surface.get_rect(center=menu_rect.center)

    screen.blit(restart_text_surface, restart_rect)
    screen.blit(menu_text_surface, menu_rect)

    return restart_rect, menu_rect, can_click_buttons

def draw_victory():
    global victory_alpha, victory_text_alpha, final_score
    victory_alpha += 5
    if victory_alpha > 255:
        victory_alpha = 255

    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, victory_alpha))
    screen.blit(overlay, (0, 0))

    victory_font = pygame.font.Font("mrsmonster.ttf", 128)
    victory_text = victory_font.render("You Win!!", True, "green")
    victory_rect = victory_text.get_rect(center=(WIDTH // 2, HEIGHT * 3 // 10 - 50)) 
    if victory_alpha < 200:
        victory_text_alpha -= 5
        if victory_text_alpha < 0:
            victory_text_alpha = 0
        inverted_overlay = pygame.Surface(victory_text.get_size(), pygame.SRCALPHA)
        inverted_overlay.fill((255, 255, 255, 255 - victory_text_alpha))
        inverted_text = victory_text.copy()
        inverted_text.blit(inverted_overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(inverted_text, victory_rect)
    else:
        screen.blit(victory_text, victory_rect)
        victory_text_alpha = 0

    # final score
    score_font = pygame.font.Font("chinesefont.ttf", 48)
    score_display = score_font.render(f"Final Score: {final_score}", True, "white")
    score_rect = score_display.get_rect(center=(WIDTH // 2, HEIGHT * 3 // 10 + 50)) 
    screen.blit(score_display, score_rect)

    # restart
    restart_color = "white"
    restart_font_normal = pygame.font.Font('BoldChinese.ttf', 48)
    restart_text_surface = restart_font_normal.render("重新開始", True, restart_color)
    restart_rect = restart_text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50)) 

    # return
    menu_color = "white"
    menu_font_normal = pygame.font.Font('BoldChinese.ttf', 48)
    menu_text_surface = menu_font_normal.render("返回選單", True, menu_color)
    menu_rect = menu_text_surface.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))

    mouse_pos = pygame.mouse.get_pos()
    can_click_buttons = (victory_alpha == 255)

    if can_click_buttons:
        if restart_rect.collidepoint(mouse_pos):
            restart_color = "green"
            restart_font_hover = pygame.font.Font('chinesefont.ttf', 36)
            restart_text_surface = restart_font_hover.render("重新開始", True, restart_color)
            restart_rect = restart_text_surface.get_rect(center=restart_rect.center)

        if menu_rect.collidepoint(mouse_pos):
            menu_color = "green"
            menu_font_hover = pygame.font.Font('chinesefont.ttf', 36)
            menu_text_surface = menu_font_hover.render("返回選單", True, menu_color)
            menu_rect = menu_text_surface.get_rect(center=menu_rect.center)

    screen.blit(restart_text_surface, restart_rect)
    screen.blit(menu_text_surface, menu_rect)

    return restart_rect, menu_rect, can_click_buttons

# Main loop
run = True  
load_images()
init_ghosts()
while run:
    timer.tick(fps)
    events = pygame.event.get() 

    for event in events:
        if event.type == pygame.QUIT:
            run = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state != "playing": 
                    game_state = "menu"

    if game_state == "menu":
        menu_rects = draw_menu()
        for event in events: 
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN:
                    selected_option = (selected_option + 1) % len(menu_options)
                elif event.key == pygame.K_UP:
                    selected_option = (selected_option - 1) % len(menu_options)
                elif event.key == pygame.K_RETURN:
                    if selected_option == 0:
                        game_state = "map_select" 
                    elif selected_option == 1:
                        game_state = "instructions"
                    elif selected_option == 2:
                        game_state = "difficulty_select" 
                    elif selected_option == 3:
                        run = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if menu_rects[0].collidepoint(mouse_pos):
                    game_state = "map_select" 
                elif menu_rects[1].collidepoint(mouse_pos):
                    game_state = "instructions"
                elif menu_rects[2].collidepoint(mouse_pos):
                    game_state = "difficulty_select" 
                elif menu_rects[3].collidepoint(mouse_pos):
                    run = False

    elif game_state == "playing":
        screen.fill("black")
        draw_board()
        draw_pacman()
        draw_ui()
        """pygame.draw.circle(screen, (255, 0, 0), (450, blinky_home[current_map]+30), 4)
        pygame.draw.circle(screen, (255, 192, 203), (450, pinky_home[current_map]+30), 4)
        pygame.draw.circle(screen, (0, 0, 255), (450, inky_home[current_map]+30), 4)
        pygame.draw.circle(screen, (255, 165, 0), (450, clyde_home[current_map]+30), 4)"""

        for ghost in ghosts:
            ghost.cooldown_timer += 1
            if collision_state:
                ghost.bfs_interval = 30
            else:
                ghost.bfs_interval = 10
                ghost_delay_counter -= 1
                if ghost.teleport_cooldown_timer < 30:
                    ghost.teleport_cooldown_timer += 1
                if not ghost_delay_counter:
                    ghost.update_path()
            #draw_path(ghost.path, screen, ((HEIGHT - 50) // 32) , (WIDTH // 30))
            if chase_mode == True:
                ghost.chase_move()
            else:
                ghost.move()
            ghost.draw()

        with_ghost_collision()

        for event in events: 
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    direction = 0
                    collision_state = False
                elif event.key == pygame.K_LEFT:
                    direction = 1
                    collision_state = False
                elif event.key == pygame.K_UP:
                    direction = 2
                    collision_state = False
                elif event.key == pygame.K_DOWN:
                    direction = 3
                    collision_state = False

        move_pacman()

        if chase_mode:
            chase_counter += 1
            if chase_counter >= chase_duration:
                chase_mode = False
                chase_counter = 0
                for ghost in ghosts:
                    ghost.sober = False
        
        if lives <= 0:
            game_state = "game_over"

        if score >= total_pellets * 10:
            game_state = "victory"
            global final_score
            final_score = score # 
            victory_alpha = 0
            victory_text_alpha = 255
            can_click_victory_buttons = False
    
    elif game_state == "instructions":
        exit_button_rect = draw_instructions()
        for event in events: 
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if exit_button_rect.collidepoint(mouse_pos):
                    game_state = "menu"

    elif game_state == "difficulty_select":
        exit_button_rect, select_buttons_rects = draw_difficulty_select()
        for event in events:
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if exit_button_rect.collidepoint(mouse_pos):
                    game_state = "menu"
                for i, rect in enumerate(select_buttons_rects):
                    if rect.collidepoint(mouse_pos):
                        selected_difficulty_index = i
                        if i == 0:
                            ghost_speed = 1
                            chase_duration = 10 * fps
                            full_health = 3
                        elif i == 1:
                            ghost_speed = 1.3
                            chase_duration = 8 * fps
                            full_health = 3
                        elif i == 2:
                            ghost_speed = 1.5
                            chase_duration = 6 * fps
                            full_health = 3
                        elif i == 3:
                            ghost_speed = 2
                            chase_duration = 4 * fps
                            full_health = 1

    elif game_state == "map_select":
        exit_button_rect, select_buttons_rects = draw_map_select()
        for event in events: 
            if event.type == pygame.QUIT:
                run = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    game_state = "menu"
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if exit_button_rect.collidepoint(mouse_pos):
                    game_state = "menu"
                for i, rect in enumerate(select_buttons_rects):
                    if rect.collidepoint(mouse_pos):
                        selected_map_index = i
                        current_map = i
                        reset_game() 
                        game_state = "playing"

    elif game_state == "game_over":
        screen.fill("black") 
        restart_button, menu_button, can_click = draw_game_over()
        can_click_game_over_buttons = can_click
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if can_click_game_over_buttons:
                    if restart_button.collidepoint(mouse_pos):
                        reset_game()
                        game_state = "playing"
                        game_over = False
                    elif menu_button.collidepoint(mouse_pos):
                        game_state = "menu"
                        game_over = False
                        game_over_alpha = 0
                        game_over_text_alpha = 255
    
    elif game_state == "victory":
        screen.fill("black")
        restart_button, menu_button, can_click = draw_victory()
        can_click_victory_buttons = can_click
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = event.pos
                if can_click_victory_buttons:
                    if restart_button.collidepoint(mouse_pos):
                        reset_game()
                        game_state = "playing"
                        game_over = False 
                    elif menu_button.collidepoint(mouse_pos):
                        game_state = "menu"
                        victory_alpha = 0
                        victory_text_alpha = 255
                        game_over = False 
    
    pygame.display.flip()

pygame.quit()
