# text_sub = """    def get_XXXX(self):
#         return self.config.get_value('scene', 'XXXX')

#     def set_XXXX(self, value: str):
#         self.config.set_value('scene', 'XXXX', value)
# """

# text_s2 = """    def set_XXXX(self, value: bool):
#         self.config.set_value('scene', 'XXXX', value)

#     def get_XXXX(self):
#         value = self.config.get_value('scene', 'XXXX')
#         try:
#             return bool(value)
#         except Exception:
#             return None
# """
# text_s3 = """        if self.get_XXXX() is None:
#             self.set_XXXX(True)
# """


# text_s4="""        if self.get_XXXX() is None:
#             self.set_XXXX('XXXX')
# """
text_s5 = """       self.set_XXXX(self.XXXX.get())"""

# items = {'show_match': "Show match (SHOW_MATCH)", 'show_results': "Show results (SHOW_RESULTS)"}
items = ['show_preview', 'show_match', 'show_results']

for x in items:
    # print("")
    # t1 = text_s2.replace('XXXX', x + '_enabled')
    # t1 = t1.replace('YYYY', y)
    # print(t1)
    # t1 = text_sub.replace('XXXX', x + '_f1_name')
    # print(t1)
    # t1 = text_sub.replace('XXXX', x+'_f2_name')
    # print(t1)
    # t1 = text_s3.replace('XXXX', x+'_enabled')
    # print(t1)
    # t1 = text_s4.replace('XXXX', x+'_f1_name')
    # print(t1)
    # t1 = text_s4.replace('XXXX', x+'_f2_name')
    # print(t1)
    t1 = text_s5.replace('XXXX', x+'_enabled')
    print(t1)
    t1 = text_s5.replace('XXXX', x+'_f1_name')
    print(t1)
    t1 = text_s5.replace('XXXX', x+'_f2_name')
    print(t1)
