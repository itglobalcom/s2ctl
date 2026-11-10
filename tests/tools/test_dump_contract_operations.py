"""tools/dump_contract_operations.py на фрагментах контроллеров publisher'а."""
import pathlib

import pytest

from tools.dump_contract_operations import (
    CONTROLLERS_DIR,
    PROJECT_DIR,
    UnresolvedRouteLiteral,
    UnterminatedAttribute,
    dump_operations,
)

_MULTILINE_ATTRIBUTE_CONTROLLER = '''
namespace Api.Controllers;

[Route("api/v1/servers")]
public class ServersController : ControllerBase
{
    /// <summary-en>Clone</summary-en>
    [HttpPost("{server_id:regex(^l\\\\d+s\\\\d+$)}/clone")]
    [RequirePermission(PanelPermissionItem.VstackCloud, PermissionAction.Edit)]
    [PossibleErrorCodes(
        ErrorCodes.Vstack.CloneSourceIsNotTurnedOff,
        // [ в комментарии не открывает атрибут
        ErrorCodes.Vstack.CloneSourceIsClone)]
    [Obsolete(
        "скобка [ в строке не открывает атрибут")]
    public async Task<IActionResult> Clone([FromRoute(Name = "server_id")] string serverId)
    {
        return Ok();
    }

    [HttpDelete("{server_id:regex(^l\\\\d+s\\\\d+$)}")]
    public async Task<IActionResult> Delete(string serverId)
    {
        return Ok();
    }
}
'''


def _publisher(tmp_path: pathlib.Path, source: str) -> pathlib.Path:
    controllers = tmp_path / PROJECT_DIR / CONTROLLERS_DIR
    controllers.mkdir(parents=True)
    (controllers / 'ServersController.cs').write_text(source, encoding='utf-8')
    return tmp_path


def test_action_with_multiline_attribute_keeps_its_operation(tmp_path):
    publisher = _publisher(tmp_path, _MULTILINE_ATTRIBUTE_CONTROLLER)

    assert dump_operations(publisher) == [
        'DELETE /api/v1/servers/{server_id}',
        'POST /api/v1/servers/{server_id}/clone',
    ]


def test_multiline_http_attribute_with_unresolved_constant_fails_the_dump(tmp_path):
    source = _MULTILINE_ATTRIBUTE_CONTROLLER.replace(
        '[HttpPost("{server_id:regex(^l\\\\d+s\\\\d+$)}/clone")]',
        '[HttpPost(\n        Routes.Clone)]',
    )
    publisher = _publisher(tmp_path, source)

    with pytest.raises(UnresolvedRouteLiteral):
        dump_operations(publisher)


def test_attribute_left_open_fails_the_dump(tmp_path):
    publisher = _publisher(tmp_path, '[Route("api/v1/servers")]\n[PossibleErrorCodes(\n    ErrorCodes.Vstack.X\n')

    with pytest.raises(UnterminatedAttribute, match=r'^\[PossibleErrorCodes\( ErrorCodes\.Vstack\.X$'):
        dump_operations(publisher)
