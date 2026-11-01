class FanCurve:
    def __init__(self, zero_rpm_temp=55, hysteresis=3, points=None):
        self.zero_rpm_temp = zero_rpm_temp  # Temperatura em °C em que as fans ligam
        self.hysteresis = hysteresis        # Margem para desligar (°C)
        self.fan_is_running = False
        
        # Pontos padrão: [(Temp °C, Fan %)]
        if points is None:
            self.points = [
                (40, 0),
                (55, 35),
                (65, 55),
                (75, 75),
                (85, 100)
            ]
        else:
            self.points = sorted(points, key=lambda p: p[0])

    def calculate_speed(self, current_temp):
        """
        Calcula a rotação percentual da ventoinha para a temperatura atual,
        respeitando o modo Zero-RPM e a histerese.
        """
        # Verificação do Zero-RPM com histerese
        turn_off_threshold = self.zero_rpm_temp - self.hysteresis

        if not self.fan_is_running:
            if current_temp >= self.zero_rpm_temp:
                self.fan_is_running = True
            else:
                return 0
        else:
            if current_temp < turn_off_threshold:
                self.fan_is_running = False
                return 0

        # Se as fans devem estar ligadas, calcula a interpolação linear pelos pontos da curva
        sorted_pts = sorted(self.points, key=lambda p: p[0])

        # Se estiver abaixo do primeiro ponto ativo
        if current_temp <= sorted_pts[0][0]:
            return sorted_pts[0][1]

        # Se estiver acima do último ponto
        if current_temp >= sorted_pts[-1][0]:
            return sorted_pts[-1][1]

        # Interpolação linear entre os dois pontos vizinhos
        for i in range(len(sorted_pts) - 1):
            t1, s1 = sorted_pts[i]
            t2, s2 = sorted_pts[i + 1]
            if t1 <= current_temp <= t2:
                if t2 == t1:
                    return s1
                factor = (current_temp - t1) / (t2 - t1)
                speed = s1 + factor * (s2 - s1)
                return int(round(speed))

        return 50

    def to_dict(self):
        return {
            "zero_rpm_temp": self.zero_rpm_temp,
            "hysteresis": self.hysteresis,
            "points": self.points
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            zero_rpm_temp=data.get("zero_rpm_temp", 55),
            hysteresis=data.get("hysteresis", 3),
            points=data.get("points", None)
        )

