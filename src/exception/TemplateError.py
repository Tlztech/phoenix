
class TemplateError(Exception):
    def __init__(self, message="模板文件错误"):
        super().__init__(self.message)
