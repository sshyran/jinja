import sys
import asyncio
import inspect

from jinja2.utils import concat, internalcode, concat, Markup


async def concat_async(async_gen):
    rv = []
    async def collect():
        async for event in async_gen:
            rv.append(event)
    await collect()
    return concat(rv)


async def render_async(self, *args, **kwargs):
    if not self.environment._async:
        raise RuntimeError('The environment was not created with async mode '
                           'enabled.')

    vars = dict(*args, **kwargs)
    ctx = self.new_context(vars)

    try:
        return await concat_async(self.root_render_func(ctx))
    except Exception:
        exc_info = sys.exc_info()
    return self.environment.handle_exception(exc_info, True)


def wrap_render_func(original_render):
    def render(self, *args, **kwargs):
        if not self.environment._async:
            return original_render(self, *args, **kwargs)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.render_async(self, *args, **kwargs))
    return render


def wrap_block_reference_call(original_call):
    @internalcode
    async def async_call(self):
        rv = await concat_async(self._stack[self._depth](self._context))
        if self._context.eval_ctx.autoescape:
            rv = Markup(rv)
        return rv

    @internalcode
    def __call__(self):
        if not self._context.environment._async:
            return original_call(self)
        return async_call(self)

    return __call__


def patch_template():
    from jinja2 import Template
    Template.render_async = render_async
    Template.render = wrap_render_func(Template.render)


def patch_runtime():
    from jinja2.runtime import BlockReference
    BlockReference.__call__ = wrap_block_reference_call(BlockReference.__call__)


def patch_all():
    patch_template()
    patch_runtime()


async def auto_await(value):
    if inspect.isawaitable(value):
        return await value
    return value
