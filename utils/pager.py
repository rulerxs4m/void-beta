import discord
from discord import ButtonStyle, ui
    
class Page(discord.Embed):
    def __init__(self, *, items: list, c: int, user, pages: list=None, index: int=0, em:discord.Embed=None, **kwargs) -> None:
        super().__init__(**kwargs)
        if em:
            if hasattr(em, "_author"): self.set_author(**em._author)
            if hasattr(em, "_footer"): self.set_footer(**em._footer)
            if hasattr(em, "_thumbnail"): self.set_thumbnail(**em._thumbnail)
            if hasattr(em, "_image"): self.set_image(**em._image)
        self.kwargs = kwargs
        self.user = user
        self.items = items
        self.pages = pages if pages else [items[x:x+c] for x in range(0, len(items), c)]
        self.index = index; self.c = c
        self.total_items = len(items)
        self.page_count = len(self.pages)
        self.view = prev_next_btns(self)
        for field in self.pages[self.index]:
            self.add_field(**field)

class prev_next_btns(ui.View):
    def __init__(self, page: Page):
        super().__init__()
        self.user = page.user
        self.page = page
        self.count_btn.label = f"{page.index+1} / {page.page_count}"
        if self.page.index == 0:
            self.first_btn.disabled = True
            self.prev_btn.disabled = True
        if self.page.index == self.page.page_count-1:
            self.next_btn.disabled = True
            self.last_btn.disabled = True
    
    @ui.button(style=ButtonStyle.gray, emoji="⏪")
    async def first_btn(self, ctx, btn):
        if (ctx.user.id != self.user.id):
            await ctx.response.send_message(f":lock: This is not for you !!! :lock:", ephemeral=True)
            return
        em = Page(
            items = self.page.items, c = self.page.c, 
            user = self.page.user, pages = self.page.pages, 
            index = 0, em = self.page, **self.page.kwargs
        )
        await ctx.response.edit_message(embed=em, view=em.view)
    
    @ui.button(style=ButtonStyle.gray, emoji="⬅️")
    async def prev_btn(self, ctx, btn):
        if (ctx.user.id != self.user.id):
            await ctx.response.send_message(f":lock: This is not for you !!! :lock:", ephemeral=True)
            return
        em = Page(
            items = self.page.items, c = self.page.c, 
            user = self.page.user, pages = self.page.pages, 
            index = self.page.index-1, em = self.page, 
            **self.page.kwargs
        )
        await ctx.response.edit_message(embed=em, view=em.view)
    
    @ui.button(style=ButtonStyle.gray, disabled=True)
    async def count_btn(self, ctx, btn): pass
    
    @ui.button(style=ButtonStyle.gray, emoji="➡️")
    async def next_btn(self, ctx, btn):
        if (ctx.user.id != self.user.id):
            await ctx.response.send_message(f":lock: This is not for you !!! :lock:", ephemeral=True)
            return
        em = Page(
            items = self.page.items, c = self.page.c, 
            user = self.page.user, pages = self.page.pages, 
            index = self.page.index+1, em = self.page, 
            **self.page.kwargs
        )
        await ctx.response.edit_message(embed=em, view=em.view)
    
    @ui.button(style=ButtonStyle.gray, emoji="⏩")
    async def last_btn(self, ctx, btn):
        if (ctx.user.id != self.user.id):
            await ctx.response.send_message(f":lock: This is not for you !!! :lock:", ephemeral=True)
            return
        em = Page(
            items = self.page.items, c = self.page.c, 
            user = self.page.user, pages = self.page.pages, 
            index = self.page.page_count-1, em = self.page, 
            **self.page.kwargs
        )
        await ctx.response.edit_message(embed=em, view=em.view)
